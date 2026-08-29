// 点点数据

const crypto = require('crypto');


function h(e, n, o) {
    var d = "";
    n = Buffer.from(n, "utf8"), o = Buffer.from(o, "utf8");
    var c = crypto.createDecipheriv("aes-128-cbc", n, o);
    return d += c.update(e, "hex", "utf8"), d += c.final("utf8")
}


function v(e, path, n, r) {
    var s = n.s
        , d = n.k
        , m = n.l
        , f = n.d
        , v = n.sort
        , l = n.num
        , k = function (content, t, e) {
        for (var a = Array.from(content), n = Array.from(t), r = a.length, o = n.length, d = String.fromCodePoint, i = 0; i < r; i++)
            a[i] = d(a[i].codePointAt(0) ^ n[(i + e) % o].codePointAt(0));
        return a.join("")
    }(function (s, t, path, e) {
        return [s, t, e, path].join("(&&)")
    }(function (t, e) {
        var n = t;
        var r = [];
        for (var d in n) {
            r.push(n[d])
        }
        return r.sort(), r.join("")
    }(e, r), parseInt((new Date).getTime() / 1e3) - 655876800 - f, path, v), h(s, d, m), l);
    return Buffer.from(k).toString("base64")
}


// e = {
//     "market_id": 1,
//     "genre_id": 0,
//     "country_id": 75,
//     "device_id": 1,
//     "page": 3,
//     "time": 1754287208,
//     "rank_type": 4,
//     "brand_id": 0
// }
//
//
// n = {
//     "s": "117fa29d4a0b30587d342a7bf21eb6d1",
//     "k": "fc33bd010bdab7ab",
//     "l": "b533518c66832815",
//     "d": -1,
//     "sort": "dd",
//     "num": 10
// }
//
//
// res = v(e, '/va/rank', n, 'get')
// console.log(res.length, res)


function params_k(e, path, n, r){
    return v(e, path, n, r)
}


