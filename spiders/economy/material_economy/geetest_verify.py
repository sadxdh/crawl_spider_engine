"""
全国企业采购交易平台 - Geetest v4 验证 + 短信发送（纯 Python 实现）

不依赖 Node.js / gcaptcha4.js，w 参数完全由 Python 纯算法生成。
"""
import hashlib
import json
import re
import secrets
import time
import uuid
import requests
from spiders.economy.material_economy.geetest_encrypt import encrypt_w
from utils.db.redis_opt import *
from loguru import logger


class cneptp_login():
    COOKIE_REDIS_KEY = 'cneptp:cookie_pool'
    SMSCODE_REDIS_KEY = 'cneptp:sms_code'

    BASE_URL = "https://account.cneptp.com"
    CAPTCHA_ID = "c22e4095d2f5c138e59c17669b1153d8"

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),
        "Referer": f"{BASE_URL}/",
    }

    # ── Geetest 内部流程 ───────────────────────────────────────────────────────────

    def _load_geetest(self) -> dict:
        resp = requests.get(
            "https://gcaptcha4.geetest.com/load",
            params={
                "captcha_id": self.CAPTCHA_ID,
                "challenge": str(uuid.uuid4()),
                "client_type": "web",
                "lang": "zh-cn",
                "callback": f"geetest_{int(time.time() * 1000)}",
            },
            headers=self._HEADERS,
            timeout=10,
        )
        raw = resp.text.strip()
        result = json.loads(raw[raw.index("(") + 1: raw.rindex(")")])
        if result.get("status") != "success":
            raise RuntimeError(f"/load 失败: {result}")
        return result["data"]

    def _compute_pow(self, lot_number: str, pow_detail: dict) -> tuple[str, str]:
        bits = int(pow_detail["bits"])
        prefix = "|".join([
            pow_detail["version"],
            str(pow_detail["bits"]),
            pow_detail["hashfunc"],
            pow_detail["datetime"],
            self.CAPTCHA_ID,
            lot_number,
            "",
        ])
        while True:
            nonce = secrets.token_hex(8)
            pow_msg = prefix + "|" + nonce
            digest = hashlib.md5(pow_msg.encode()).hexdigest()
            if bits == 0:
                return pow_msg, digest
            bin_str = bin(int(digest, 16))[2:].zfill(128)
            if bin_str[:bits] == "0" * bits:
                return pow_msg, digest

    def _build_plaintext(self, lot_number: str, pow_msg: str, pow_sign: str) -> dict:
        dyn_key = lot_number[1:5]
        dyn_val = lot_number[24:28]
        return {
            dyn_key: dyn_val,
            "device_id": "",
            "lot_number": lot_number,
            "pow_msg": pow_msg,
            "pow_sign": pow_sign,
            "YYhg": "BjI0",
        }

    def _encrypt_w(self, plaintext: dict, pt: str) -> str:
        plain_json = json.dumps(plaintext, separators=(",", ":"), ensure_ascii=False)
        return encrypt_w(plain_json, pt)

    # ── 公共 API ───────────────────────────────────────────────────────────────────

    def geetest_verify(self, max_retries: int = 3) -> dict:
        for attempt in range(1, max_retries + 1):
            data = self._load_geetest()
            lot_number = data["lot_number"]
            pt = str(data.get("pt", "1"))

            pow_msg, pow_sign = self._compute_pow(lot_number, data["pow_detail"])
            w = self._encrypt_w(self._build_plaintext(lot_number, pow_msg, pow_sign), pt)

            resp = requests.get(
                "https://gcaptcha4.geetest.com/verify",
                params={
                    "captcha_id": self.CAPTCHA_ID,
                    "client_type": "web",
                    "lot_number": lot_number,
                    "payload": data.get("payload", ""),
                    "process_token": data.get("process_token", ""),
                    "payload_protocol": data.get("payload_protocol", "1"),
                    "pt": pt,
                    "w": w,
                    "callback": f"geetest_{int(time.time() * 1000)}",
                },
                headers=self._HEADERS,
                timeout=10,
            )
            raw = resp.text.strip()
            result = json.loads(raw[raw.index("(") + 1: raw.rindex(")")])

            if result.get("status") != "success":
                raise RuntimeError(f"/verify status 非 success: {result}")

            vdata = result["data"]
            if vdata.get("result") == "success":
                return vdata

            print(f"[{attempt}/{max_retries}] /verify result=continue，等待重试…")
            if attempt < max_retries:
                time.sleep(2)

        raise RuntimeError(
            f"/verify 连续 {max_retries} 次返回 result=continue，"
            "当前 IP 被 Geetest 风控，建议更换代理后重试。"
        )

    def send_sms(self, mobile: str, business_type: int = 2, account_type: int = 2) -> dict:
        gee = self.geetest_verify()
        seccode = gee["seccode"]
        payload = {
            "userMobile": mobile,
            "businessType": business_type,
            "accountType": account_type,
            "behaviorValidate": {
                "lotNumber": gee["lot_number"],
                "captchaOutput": seccode["captcha_output"],
                "passToken": seccode["pass_token"],
                "genTime": seccode["gen_time"],
            },
        }
        resp = requests.post(
            f"{self.BASE_URL}/prod-api/passport/user/send/sms",
            data=json.dumps(payload, separators=(",", ":")),
            headers={**self._HEADERS, "Content-Type": "application/json;charset=UTF-8",
                     "Origin": self.BASE_URL},
            timeout=10,
        )
        return resp.json()

    def login(
            self,
            mobile: str,
            sms_uuid: str,
            code: str,
            redirect: str = "https://www.cneptp.com/index",
            app_key: str = "782b259830834cdcbe61c51c9a73e889",
            cookies: dict | None = None,
    ) -> dict:
        payload = {
            "userMobile": mobile,
            "smsUuid": sms_uuid,
            "code": code,
            "keepLogin": 1,
            "loginType": 2,
            "accountType": 2,
            "redirect": redirect,
            "serverType": 2,
            "appKey": app_key,
        }
        resp = requests.post(
            f"{self.BASE_URL}/prod-api/passport/user/login",
            data=json.dumps(payload, separators=(",", ":")),
            headers={**self._HEADERS, "Content-Type": "application/json;charset=UTF-8",
                     "Origin": self.BASE_URL},
            cookies=cookies,
            timeout=10,
        )
        logger.info(resp.text)
        return resp.json()

    def get_login(self):
        cookies = {}
        account_dict = hgetall(self.COOKIE_REDIS_KEY)
        for mobile, token in account_dict.items():
            logger.info(f"发送验证码 → {mobile}")
            sms_result = self.send_sms(mobile.decode("utf-8"))
            logger.info(json.dumps(sms_result, ensure_ascii=False, indent=2))

            sms_uuid = sms_result.get("data", "")
            time.sleep(20)
            code_content = str_get(self.SMSCODE_REDIS_KEY).decode("utf-8")
            code = re.search(r"验证码[：:]\s*(\d+)", code_content).group(1)
            login_result = self.login(mobile.decode("utf-8"), sms_uuid, code)
            ztoken = login_result['data']['token']
            cookies['zToken'] = ztoken
            hset(self.COOKIE_REDIS_KEY, mobile.decode("utf-8"), json.dumps(cookies))
        return cookies