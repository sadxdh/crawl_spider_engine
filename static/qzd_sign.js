
// 企知道签名算法

const path = require('path');
let CryptoJS;
const platform = process.platform;
if (platform === 'linux') {
    CryptoJS = require('crypto-js')
} else {
    CryptoJS = require('crypto-js');
}


function gen_md5(e) {
    return CryptoJS.MD5(e).toString();
}

function gen_sha1(data) {
    const hash = CryptoJS.SHA1(data);
    // 获取哈希值的十六进制表示
    return hash.toString(CryptoJS.enc.Hex);
}



//--------------------------------------------------------------------------------------------------------------
// 39位的签名名算法
function get_sign(A, e = undefined) {
    var n = function (A, e, n) {
        var t, r = "";
        void 0 === A && (A = 6),
        "string" == typeof e && (n = e),
            t = e && "number" == typeof e ? Math.round(Math.random() * (e - A)) + A : A,
            n = n || "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        for (var s = 0; s < t; s++) {
            var i = Math.round(Math.random() * (n.length - 1));
            r += n.substring(i, i + 1)
        }
        return r
    }()
        , t = gen_md5(n);
    return gen_md5(t + A + e) + "." + n
}


// -----------------------------------------------------------------------------------------
// 40位的签名算法

function u() {
    var e = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {}
        , t = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : [];
    return Object.keys(e).forEach((function (n) {
            "[object Array]" === Object.prototype.toString.call(e[n]) || "[object Object]" === Object.prototype.toString.call(e[n]) ? u(e[n], t) : (e[n] || 0 === e[n] || e[n] + "" == "false") && t.push(e[n] + "")
        }
    )),
        t
}


function trans_list(e) {
    return function (e) {
        if (Array.isArray(e))
            return trans_list(e)
    }(e) || gen_md5(e) || function () {
        throw new TypeError("Invalid attempt to spread non-iterable instance.In order to be iterable, non-array objects must have a [Symbol.iterator]() method.")
    }()
}

function get_signature(e) {
    var t = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : ""
        , n = new Set(u(e).map((function (e) {
            return e + ""
        }
    )))
        , i = Array.from(n)
        , o = i.sort().join("");
    return t ? gen_md5(gen_sha1(gen_md5(o)) + t) : gen_sha1(gen_md5(o))
}


// ----------------------------------------------------------------------------------------------------------
// 签名算法调用

function get_signature_39(token, param_sign = 6) {
    return get_sign(token, param_sign)
}


function get_signature_40(data) {
    return get_signature(data)
}


module.exports = { get_signature_39, get_signature_40, get_signature };
