window = this;
var uuidCount = 0


var m = function() {
    function t() {
        this.codeStr = "",
        this.pubPass = "BX1o65CoobwcDP33iQW6ld1OyIPsNzF1",
        this.pubPassNum = [],
        this.publicKey = "",
        this.setPass(this.pubPass)
    }
    return t.prototype.encode = function(t) {
        var n = "";
        try {
            n = JSON.stringify(t)
        } catch (e) {
            return console.error(e + "这不是一个正确的json对象"),
            ""
        }
        return this.encryptCode(n)
    }
    ,
    t.prototype.decode = function(t) {
        var n;
        try {
            n = JSON.parse(this.decryptCode(t))
        } catch (e) {
            return void console.error(e + "json对象转出失败")
        }
        return n
    }
    ,
    t.prototype.encryptCode = function(t) {
        for (var n = encodeURI(t), e = [], i = 0, r = "", o = this.random(16, 32), s = this.randomStr(o), a = this.stringChangeASCIINumberArrs(s), u = 0, c = 0, h = 0, p = 0; p < n.length; p++)
            i = n.charCodeAt(p),
            u == this.pubPassNum.length && (u = 0),
            i += this.pubPassNum[u],
            u++,
            c == a.length && (c = 0),
            i += a[c],
            c++,
            h += i,
            h > 65535 && (h -= 65535),
            r = i.toString(36),
            r = ("00" + r).substr(-2, 2),
            1 == r.length && (r = "0" + r),
            e.push(r);
        var l = "";
        return l = h.toString(36),
        l = ("0000" + r).substr(-4, 4),
        e.unshift(s),
        e.unshift(o.toString(36)),
        e.unshift(l),
        e.join("")
    }
    ,
    t.prototype.decryptCode = function(t) {
        var n = ""
          , e = 0
          , i = ""
          , r = []
          , o = []
          , s = 0
          , a = 0;
        n = t.substr(4, 1),
        e = parseInt(n, 36),
        i = t.substr(5, e),
        r = this.stringChangeASCIINumberArrs(i),
        n = t.substr(5 + e, t.length - 5 - e);
        for (var u = "", c = 0, h = 0, p = 0; p < n.length / 2; p++)
            u = n.substr(h, 2),
            h += 2,
            c = parseInt(u, 36),
            a == r.length && (a = 0),
            c -= r[a],
            a++,
            s == this.pubPass.length && (s = 0),
            c -= this.pubPassNum[s],
            s++,
            u = String.fromCharCode(c),
            o.push(u);
        return n = o.join(""),
        n = decodeURI(n),
        n
    }
    ,
    t.prototype.setPass = function(t) {
        this.pubPassNum = this.stringChangeASCIINumberArrs(t)
    }
    ,
    t.prototype.stringChangeASCIINumberArrs = function(t) {
        for (var n = [], e = 0; e < t.length; e++)
            n.push(t.charCodeAt(e));
        return n
    }
    ,
    t.prototype.random = function(t, n) {
        return void 0 === t && (t = 0),
        void 0 === n && (n = 1e4),
        Math.floor(Math.random() * (n - t) + t)
    }
    ,
    t.prototype.randomStr = function(t) {
        for (var n = [], e = 0; e < t; e++)
            n.push(this.random(0, 35).toString(36));
        return n.join("")
    }
    ,
    t
}()


var uuid = function(n, e) {
    void 0 === n && (n = 16),
    void 0 === e && (e = !1),
    !e && n < 16 && (console.error("uuid useCase=false 时 len 不能小于 16"),
    n = 16),
    e && n < 12 && (console.error("uuid useCase=true 时 len 不能小于 12"),
    n = 12);
    var i = ((new Date).getTime() + 1e14).toString();
    return i += ("000" + (++uuidCount).toString()).substr(-3, 3),
    i = e ? parseInt(i).to62() : parseInt(i).toString(36),
    i += instance.randomStr(n),
    i = i.substr(0, n),
    i
}


var instance = new m();


function decode(t){
    return instance.decode(t)
}

function encode(t){
    return instance.encode(t)
}

function gen_uuid() {
    return uuid(16, false)
}

function gen_data(page) {
    const data = {
        "id": gen_uuid(),
        "projectKey": "honsan_cloud_ccprec",
        "clientKey": gen_uuid(),
        "token": null,
        "clientDailyData": {},
        "acts": [{
            "id": gen_uuid(),
            "fullPath": "/cloud.sys.tomcatV11/api/v1/template/getPages",
            "args": [{
                "data": {
                    "templateId": "47e6544fca0b47d79159b9b62a3a56ab",
                    "pageNo": page,
                    "pageSize": 15,
                    "where": {
                        "type": "qxb_xfpzh"
                    }
                }
            }]
        }]
    }
    var data_str = JSON.stringify(data)
    return encode(data_str)
}
