let cookie = {}


function setCookie(e, t, n) {
    var r, o = new Date;
    o.setTime(o.getTime() + 36e5 * (n || 12)),
        r = "cspea.com.cn";
    var i = encodeURI(t)
    cookie[e] = i
}


// 第一步：e=18339180133,
function setAuthKey(e) {
    e && setCookie("CSPEA_AUTHKEY", e = 18339180133)
}


//第三步 e=1753153898000  时间戳
function setLastLoginTime(e) {
    e && setCookie("CSPEA_LAST_LOGIN_TIME", e)
}

//第四步 e='{"insCode":null,"org":null,"wechatCount":0,"memberLevel":null,"mobile":"18339180133","industry":null,"qqNumber":null,"userName":"18339180133","experience":null,"userId":"4aa0a08e02bd4342b0dd6f3000907ca9","groupNumber":"0","memberExpiryDate":null,"realName":null,"userState":"0","phone":null,"position":null,"department":null,"email":null}'
function setUserInfo(e) {
    e && setCookie("CSPEA_USER", e)
}


//生成cookie
function generate_cookie(phone, time_stamp, user_info){
    setAuthKey(phone)
    setLastLoginTime(time_stamp)
    setUserInfo(user_info)
    return cookie
}
