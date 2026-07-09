"use strict";
var $s = Object.create;
var Pt = Object.defineProperty;
var Vs = Object.getOwnPropertyDescriptor;
var qs = Object.getOwnPropertyNames;
var Hs = Object.getPrototypeOf,
  Ks = Object.prototype.hasOwnProperty;
var Us = (_, y, r) =>
  y in _
    ? Pt(_, y, { enumerable: !0, configurable: !0, writable: !0, value: r })
    : (_[y] = r);
var vn = (_, y) => () => (y || _((y = { exports: {} }).exports, y), y.exports),
  Ws = (_, y) => {
    for (var r in y) Pt(_, r, { get: y[r], enumerable: !0 });
  },
  En = (_, y, r, n) => {
    if ((y && typeof y == "object") || typeof y == "function")
      for (let i of qs(y))
        !Ks.call(_, i) &&
          i !== r &&
          Pt(_, i, {
            get: () => y[i],
            enumerable: !(n = Vs(y, i)) || n.enumerable,
          });
    return _;
  };
var ae = (_, y, r) => (
    (r = _ != null ? $s(Hs(_)) : {}),
    En(
      y || !_ || !_.__esModule
        ? Pt(r, "default", { value: _, enumerable: !0 })
        : r,
      _
    )
  ),
  Zs = (_) => En(Pt({}, "__esModule", { value: !0 }), _);
var Xe = (_, y, r) => Us(_, typeof y != "symbol" ? y + "" : y, r);
var Sr = vn((oa, Gs) => {
  Gs.exports = {
    versions: [
      {
        version: "1.5.15",
        date: "2026-06-01",
        title:
          "\u5168\u6587\u5B58\u50A8\u91CD\u6784 + OCR \u9605\u8BFB\u987A\u5E8F\u4FEE\u590D + Redo \u4E00\u952E\u91CD\u505A",
        breaking_or_migration: [
          "\u5168\u6587\u6587\u4EF6\u73B0\u5728\u7EDF\u4E00\u5B58\u653E\u4E8E System/PaperForge/ocr/ \u4E0B\uFF0C\u4E0D\u518D\u5728\u5DE5\u4F5C\u533A\u4FDD\u7559\u526F\u672C",
          "Redo OCR \u73B0\u5728\u4F1A\u7ACB\u5373\u6267\u884C\uFF08\u4E00\u952E\u5B8C\u6210\uFF09\uFF0C\u4E0D\u518D\u9700\u8981\u624B\u52A8\u518D\u8DD1\u4E00\u6B21",
        ],
        new_features: [
          "Redo OCR \u4E00\u952E\u95ED\u73AF\uFF1A\u52FE\u9009 \u2192 \u70B9\u6309\u94AE \u2192 \u81EA\u52A8\u5B8C\u6210\u5168\u90E8\u6D41\u7A0B",
          "\u8BBE\u7F6E\u9875\u65B0\u589E\u300C\u66F4\u65B0\u4E0E\u624B\u518C\u300D\u6807\u7B7E\u9875\uFF0C\u53EF\u968F\u65F6\u67E5\u770B\u7248\u672C\u66F4\u65B0\u8BB0\u5F55\u548C\u4F7F\u7528\u624B\u518C",
          "\u63D2\u4EF6\u66F4\u65B0\u540E\u81EA\u52A8\u5F39\u51FA\u66F4\u65B0\u8BF4\u660E",
        ],
        fixes: [
          "\u4FEE\u590D\u5168\u6587\u9605\u8BFB\u987A\u5E8F\u6DF7\u4E71\uFF0C\u4F18\u5316\u6574\u4F53\u6392\u7248\u4F53\u9A8C",
          "\u4FEE\u590D\u7AE0\u8282\u6807\u9898\u548C\u6B63\u6587\u6BB5\u843D\u9519\u4F4D\u65AD\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u56FE\u8868\u548C\u5BF9\u5E94\u56FE\u6CE8\u88AB\u5206\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u9996\u9875\u6458\u8981\u533A\u5757\u6392\u5E8F\u5F02\u5E38",
          "\u4FEE\u590D\u5E76\u6392\u56FE\u7247\u672A\u80FD\u81EA\u52A8\u5408\u5E76\u7684\u95EE\u9898",
          "Dashboard \u73B0\u5728\u80FD\u6B63\u786E\u8BC6\u522B\u65B0\u7684\u5168\u6587\u6587\u4EF6\u4F4D\u7F6E",
        ],
        recommended_actions: [
          "\u65E7\u7248 OCR \u5168\u6587\u53EF\u80FD\u5B58\u5728\u9605\u8BFB\u987A\u5E8F\u95EE\u9898\uFF0C\u5EFA\u8BAE\u5BF9\u91CD\u8981\u8BBA\u6587\u6267\u884C\u4E00\u6B21 Redo OCR",
          "\u6253\u5F00\u5168\u6587\u8BF7\u76F4\u63A5\u4F7F\u7528 Dashboard \u7684\u300C\u6253\u5F00\u5168\u6587\u300D\u6309\u94AE",
        ],
      },
    ],
  };
});
var Zn = vn((nr, Ot) => {
  var tr = void 0,
    rr = function (_) {
      return (
        tr ||
        ((tr = new Promise(function (y, r) {
          var cn, pn;
          var n = typeof _ != "undefined" ? _ : {},
            i = n.onAbort;
          ((n.onAbort = function (e) {
            (r(new Error(e)), i && i(e));
          }),
            (n.postRun = n.postRun || []),
            n.postRun.push(function () {
              y(n);
            }),
            (Ot = void 0));
          var a;
          a || (a = typeof n != "undefined" ? n : {});
          var c = !!globalThis.window,
            l = !!globalThis.WorkerGlobalScope;
          a.onRuntimeInitialized = function () {
            function e(m, T) {
              switch (typeof T) {
                case "boolean":
                  js(m, T ? 1 : 0);
                  break;
                case "number":
                  Ls(m, T);
                  break;
                case "string":
                  Is(m, T, -1, -1);
                  break;
                case "object":
                  if (T === null) _n(m);
                  else if (T.length != null) {
                    var L = Ht(T.length);
                    (F.set(T, L), Ns(m, L, T.length, -1), St(L));
                  } else
                    Zt(
                      m,
                      "Wrong API use : tried to return a value of an unknown type (" +
                        T +
                        ").",
                      -1
                    );
                  break;
                default:
                  _n(m);
              }
            }
            function t(m, T) {
              for (var L = [], N = 0; N < m; N += 1) {
                var W = fe(T + 4 * N, "i32"),
                  ee = Ds(W);
                if (ee === 1 || ee === 2) W = Ms(W);
                else if (ee === 3) W = Bs(W);
                else if (ee === 4) {
                  ((ee = W), (W = As(ee)), (ee = Os(ee)));
                  for (var Be = new Uint8Array(W), Re = 0; Re < W; Re += 1)
                    Be[Re] = F[ee + Re];
                  W = Be;
                } else W = null;
                L.push(W);
              }
              return L;
            }
            function s(m, T) {
              ((this.Qa = m), (this.db = T), (this.Oa = 1), (this.yb = []));
            }
            function o(m, T) {
              if (((this.db = T), (this.ob = qt(m)), this.ob === null))
                throw Error("Unable to allocate memory for the SQL string");
              ((this.ub = this.ob), (this.gb = this.Fb = null));
            }
            function d(m) {
              if (
                ((this.filename =
                  "dbfile_" + ((4294967295 * Math.random()) >>> 0)),
                m != null)
              ) {
                var T = this.filename,
                  L = "/",
                  N = T;
                if (
                  (L &&
                    ((L = typeof L == "string" ? L : lr(L)),
                    (N = T ? ce(L + "/" + T) : L)),
                  (T = jr(!0, !0)),
                  (N = os(N, T)),
                  m)
                ) {
                  if (typeof m == "string") {
                    L = Array(m.length);
                    for (var W = 0, ee = m.length; W < ee; ++W)
                      L[W] = m.charCodeAt(W);
                    m = L;
                  }
                  (jt(N, T | 146),
                    (L = ft(N, 577)),
                    en(L, m, 0, m.length, 0),
                    hr(L),
                    jt(N, T));
                }
              }
              (this.handleError($(this.filename, E)),
                (this.db = fe(E, "i32")),
                yn(this.db),
                (this.pb = {}),
                (this.Sa = {}));
            }
            var E = st(4),
              P = a.cwrap,
              $ = P("sqlite3_open", "number", ["string", "number"]),
              Q = P("sqlite3_close_v2", "number", ["number"]),
              Z = P("sqlite3_exec", "number", [
                "number",
                "string",
                "number",
                "number",
                "number",
              ]),
              Y = P("sqlite3_changes", "number", ["number"]),
              _e = P("sqlite3_prepare_v2", "number", [
                "number",
                "string",
                "number",
                "number",
                "number",
              ]),
              ht = P("sqlite3_sql", "string", ["number"]),
              un = P("sqlite3_normalized_sql", "string", ["number"]),
              dn = P("sqlite3_prepare_v2", "number", [
                "number",
                "number",
                "number",
                "number",
                "number",
              ]),
              gs = P("sqlite3_bind_text", "number", [
                "number",
                "number",
                "number",
                "number",
                "number",
              ]),
              fn = P("sqlite3_bind_blob", "number", [
                "number",
                "number",
                "number",
                "number",
                "number",
              ]),
              _s = P("sqlite3_bind_double", "number", [
                "number",
                "number",
                "number",
              ]),
              ms = P("sqlite3_bind_int", "number", [
                "number",
                "number",
                "number",
              ]),
              ys = P("sqlite3_bind_parameter_index", "number", [
                "number",
                "string",
              ]),
              bs = P("sqlite3_step", "number", ["number"]),
              vs = P("sqlite3_errmsg", "string", ["number"]),
              Es = P("sqlite3_column_count", "number", ["number"]),
              xs = P("sqlite3_data_count", "number", ["number"]),
              ws = P("sqlite3_column_double", "number", ["number", "number"]),
              hn = P("sqlite3_column_text", "string", ["number", "number"]),
              ks = P("sqlite3_column_blob", "number", ["number", "number"]),
              Ss = P("sqlite3_column_bytes", "number", ["number", "number"]),
              Ps = P("sqlite3_column_type", "number", ["number", "number"]),
              Cs = P("sqlite3_column_name", "string", ["number", "number"]),
              Fs = P("sqlite3_reset", "number", ["number"]),
              Rs = P("sqlite3_clear_bindings", "number", ["number"]),
              Ts = P("sqlite3_finalize", "number", ["number"]),
              gn = P(
                "sqlite3_create_function_v2",
                "number",
                "number string number number number number number number number".split(
                  " "
                )
              ),
              Ds = P("sqlite3_value_type", "number", ["number"]),
              As = P("sqlite3_value_bytes", "number", ["number"]),
              Bs = P("sqlite3_value_text", "string", ["number"]),
              Os = P("sqlite3_value_blob", "number", ["number"]),
              Ms = P("sqlite3_value_double", "number", ["number"]),
              Ls = P("sqlite3_result_double", "", ["number", "number"]),
              _n = P("sqlite3_result_null", "", ["number"]),
              Is = P("sqlite3_result_text", "", [
                "number",
                "string",
                "number",
                "number",
              ]),
              Ns = P("sqlite3_result_blob", "", [
                "number",
                "number",
                "number",
                "number",
              ]),
              js = P("sqlite3_result_int", "", ["number", "number"]),
              Zt = P("sqlite3_result_error", "", [
                "number",
                "string",
                "number",
              ]),
              mn = P("sqlite3_aggregate_context", "number", [
                "number",
                "number",
              ]),
              yn = P("RegisterExtensionFunctions", "number", ["number"]),
              bn = P("sqlite3_update_hook", "number", [
                "number",
                "number",
                "number",
              ]);
            ((s.prototype.bind = function (m) {
              if (!this.Qa) throw "Statement closed";
              return (
                this.reset(),
                Array.isArray(m)
                  ? this.Wb(m)
                  : m != null && typeof m == "object"
                    ? this.Xb(m)
                    : !0
              );
            }),
              (s.prototype.step = function () {
                if (!this.Qa) throw "Statement closed";
                this.Oa = 1;
                var m = bs(this.Qa);
                switch (m) {
                  case 100:
                    return !0;
                  case 101:
                    return !1;
                  default:
                    throw this.db.handleError(m);
                }
              }),
              (s.prototype.Pb = function (m) {
                return (
                  m == null && ((m = this.Oa), (this.Oa += 1)),
                  ws(this.Qa, m)
                );
              }),
              (s.prototype.hc = function (m) {
                if (
                  (m == null && ((m = this.Oa), (this.Oa += 1)),
                  (m = hn(this.Qa, m)),
                  typeof BigInt != "function")
                )
                  throw Error("BigInt is not supported");
                return BigInt(m);
              }),
              (s.prototype.mc = function (m) {
                return (
                  m == null && ((m = this.Oa), (this.Oa += 1)),
                  hn(this.Qa, m)
                );
              }),
              (s.prototype.getBlob = function (m) {
                m == null && ((m = this.Oa), (this.Oa += 1));
                var T = Ss(this.Qa, m);
                m = ks(this.Qa, m);
                for (var L = new Uint8Array(T), N = 0; N < T; N += 1)
                  L[N] = F[m + N];
                return L;
              }),
              (s.prototype.get = function (m, T) {
                ((T = T || {}),
                  m != null && this.bind(m) && this.step(),
                  (m = []));
                for (var L = xs(this.Qa), N = 0; N < L; N += 1)
                  switch (Ps(this.Qa, N)) {
                    case 1:
                      var W = T.useBigInt ? this.hc(N) : this.Pb(N);
                      m.push(W);
                      break;
                    case 2:
                      m.push(this.Pb(N));
                      break;
                    case 3:
                      m.push(this.mc(N));
                      break;
                    case 4:
                      m.push(this.getBlob(N));
                      break;
                    default:
                      m.push(null);
                  }
                return m;
              }),
              (s.prototype.Db = function () {
                for (var m = [], T = Es(this.Qa), L = 0; L < T; L += 1)
                  m.push(Cs(this.Qa, L));
                return m;
              }),
              (s.prototype.Ob = function (m, T) {
                ((m = this.get(m, T)), (T = this.Db()));
                for (var L = {}, N = 0; N < T.length; N += 1) L[T[N]] = m[N];
                return L;
              }),
              (s.prototype.lc = function () {
                return ht(this.Qa);
              }),
              (s.prototype.ic = function () {
                return un(this.Qa);
              }),
              (s.prototype.Jb = function (m) {
                return (m != null && this.bind(m), this.step(), this.reset());
              }),
              (s.prototype.Lb = function (m, T) {
                (T == null && ((T = this.Oa), (this.Oa += 1)),
                  (m = qt(m)),
                  this.yb.push(m),
                  this.db.handleError(gs(this.Qa, T, m, -1, 0)));
              }),
              (s.prototype.Vb = function (m, T) {
                T == null && ((T = this.Oa), (this.Oa += 1));
                var L = Ht(m.length);
                (F.set(m, L),
                  this.yb.push(L),
                  this.db.handleError(fn(this.Qa, T, L, m.length, 0)));
              }),
              (s.prototype.Kb = function (m, T) {
                (T == null && ((T = this.Oa), (this.Oa += 1)),
                  this.db.handleError(
                    (m === (m | 0) ? ms : _s)(this.Qa, T, m)
                  ));
              }),
              (s.prototype.Yb = function (m) {
                (m == null && ((m = this.Oa), (this.Oa += 1)),
                  fn(this.Qa, m, 0, 0, 0));
              }),
              (s.prototype.Mb = function (m, T) {
                switch (
                  (T == null && ((T = this.Oa), (this.Oa += 1)), typeof m)
                ) {
                  case "string":
                    this.Lb(m, T);
                    return;
                  case "number":
                    this.Kb(m, T);
                    return;
                  case "bigint":
                    this.Lb(m.toString(), T);
                    return;
                  case "boolean":
                    this.Kb(m + 0, T);
                    return;
                  case "object":
                    if (m === null) {
                      this.Yb(T);
                      return;
                    }
                    if (m.length != null) {
                      this.Vb(m, T);
                      return;
                    }
                }
                throw (
                  "Wrong API use : tried to bind a value of an unknown type (" +
                  m +
                  ")."
                );
              }),
              (s.prototype.Xb = function (m) {
                var T = this;
                return (
                  Object.keys(m).forEach(function (L) {
                    var N = ys(T.Qa, L);
                    N !== 0 && T.Mb(m[L], N);
                  }),
                  !0
                );
              }),
              (s.prototype.Wb = function (m) {
                for (var T = 0; T < m.length; T += 1) this.Mb(m[T], T + 1);
                return !0;
              }),
              (s.prototype.reset = function () {
                return (this.Cb(), Rs(this.Qa) === 0 && Fs(this.Qa) === 0);
              }),
              (s.prototype.Cb = function () {
                for (var m; (m = this.yb.pop()) !== void 0; ) St(m);
              }),
              (s.prototype.cb = function () {
                this.Cb();
                var m = Ts(this.Qa) === 0;
                return (delete this.db.pb[this.Qa], (this.Qa = 0), m);
              }),
              (o.prototype.next = function () {
                if (this.ob === null) return { done: !0 };
                if (
                  (this.gb !== null && (this.gb.cb(), (this.gb = null)),
                  !this.db.db)
                )
                  throw (this.Ab(), Error("Database closed"));
                var m = Ut(),
                  T = st(4);
                (De(E), De(T));
                try {
                  (this.db.handleError(dn(this.db.db, this.ub, -1, E, T)),
                    (this.ub = fe(T, "i32")));
                  var L = fe(E, "i32");
                  return L === 0
                    ? (this.Ab(), { done: !0 })
                    : ((this.gb = new s(L, this.db)),
                      (this.db.pb[L] = this.gb),
                      { value: this.gb, done: !1 });
                } catch (N) {
                  throw ((this.Fb = j(this.ub)), this.Ab(), N);
                } finally {
                  Kt(m);
                }
              }),
              (o.prototype.Ab = function () {
                (St(this.ob), (this.ob = null));
              }),
              (o.prototype.jc = function () {
                return this.Fb !== null ? this.Fb : j(this.ub);
              }),
              typeof Symbol == "function" &&
                typeof Symbol.iterator == "symbol" &&
                (o.prototype[Symbol.iterator] = function () {
                  return this;
                }),
              (d.prototype.Jb = function (m, T) {
                if (!this.db) throw "Database closed";
                if (T) {
                  m = this.Gb(m, T);
                  try {
                    m.step();
                  } finally {
                    m.cb();
                  }
                } else this.handleError(Z(this.db, m, 0, 0, E));
                return this;
              }),
              (d.prototype.exec = function (m, T, L) {
                if (!this.db) throw "Database closed";
                var N = null,
                  W = null,
                  ee = null;
                try {
                  ee = W = qt(m);
                  var Be = st(4);
                  for (m = []; fe(ee, "i8") !== 0; ) {
                    (De(E),
                      De(Be),
                      this.handleError(dn(this.db, ee, -1, E, Be)));
                    var Re = fe(E, "i32");
                    if (((ee = fe(Be, "i32")), Re !== 0)) {
                      var Se = null;
                      for (
                        N = new s(Re, this), T != null && N.bind(T);
                        N.step();
                      )
                        (Se === null &&
                          ((Se = { columns: N.Db(), values: [] }), m.push(Se)),
                          Se.values.push(N.get(null, L)));
                      N.cb();
                    }
                  }
                  return m;
                } catch (Oe) {
                  throw (N && N.cb(), Oe);
                } finally {
                  W && St(W);
                }
              }),
              (d.prototype.ec = function (m, T, L, N, W) {
                (typeof T == "function" && ((N = L), (L = T), (T = void 0)),
                  (m = this.Gb(m, T)));
                try {
                  for (; m.step(); ) L(m.Ob(null, W));
                } finally {
                  m.cb();
                }
                if (typeof N == "function") return N();
              }),
              (d.prototype.Gb = function (m, T) {
                if (
                  (De(E),
                  this.handleError(_e(this.db, m, -1, E, 0)),
                  (m = fe(E, "i32")),
                  m === 0)
                )
                  throw "Nothing to prepare";
                var L = new s(m, this);
                return (T != null && L.bind(T), (this.pb[m] = L));
              }),
              (d.prototype.pc = function (m) {
                return new o(m, this);
              }),
              (d.prototype.fc = function () {
                (Object.values(this.pb).forEach(function (T) {
                  T.cb();
                }),
                  Object.values(this.Sa).forEach(Ge),
                  (this.Sa = {}),
                  this.handleError(Q(this.db)));
                var m = ls(this.filename);
                return (
                  this.handleError($(this.filename, E)),
                  (this.db = fe(E, "i32")),
                  yn(this.db),
                  m
                );
              }),
              (d.prototype.close = function () {
                this.db !== null &&
                  (Object.values(this.pb).forEach(function (m) {
                    m.cb();
                  }),
                  Object.values(this.Sa).forEach(Ge),
                  (this.Sa = {}),
                  this.fb && (Ge(this.fb), (this.fb = void 0)),
                  this.handleError(Q(this.db)),
                  Jr("/" + this.filename),
                  (this.db = null));
              }),
              (d.prototype.handleError = function (m) {
                if (m === 0) return null;
                throw ((m = vs(this.db)), Error(m));
              }),
              (d.prototype.kc = function () {
                return Y(this.db);
              }),
              (d.prototype.bc = function (m, T) {
                Object.prototype.hasOwnProperty.call(this.Sa, m) &&
                  (Ge(this.Sa[m]), delete this.Sa[m]);
                var L = kt(function (N, W, ee) {
                  W = t(W, ee);
                  try {
                    var Be = T.apply(null, W);
                  } catch (Re) {
                    Zt(N, Re, -1);
                    return;
                  }
                  e(N, Be);
                }, "viii");
                return (
                  (this.Sa[m] = L),
                  this.handleError(gn(this.db, m, T.length, 1, 0, L, 0, 0, 0)),
                  this
                );
              }),
              (d.prototype.ac = function (m, T) {
                var L =
                    T.init ||
                    function () {
                      return null;
                    },
                  N =
                    T.finalize ||
                    function (Se) {
                      return Se;
                    },
                  W = T.step;
                if (!W)
                  throw (
                    "An aggregate function must have a step function in " + m
                  );
                var ee = {};
                (Object.hasOwnProperty.call(this.Sa, m) &&
                  (Ge(this.Sa[m]), delete this.Sa[m]),
                  (T = m + "__finalize"),
                  Object.hasOwnProperty.call(this.Sa, T) &&
                    (Ge(this.Sa[T]), delete this.Sa[T]));
                var Be = kt(function (Se, Oe, Er) {
                    var at = mn(Se, 1);
                    (Object.hasOwnProperty.call(ee, at) || (ee[at] = L()),
                      (Oe = t(Oe, Er)),
                      (Oe = [ee[at]].concat(Oe)));
                    try {
                      ee[at] = W.apply(null, Oe);
                    } catch (zs) {
                      (delete ee[at], Zt(Se, zs, -1));
                    }
                  }, "viii"),
                  Re = kt(function (Se) {
                    var Oe = mn(Se, 1);
                    try {
                      var Er = N(ee[Oe]);
                    } catch (at) {
                      (delete ee[Oe], Zt(Se, at, -1));
                      return;
                    }
                    (e(Se, Er), delete ee[Oe]);
                  }, "vi");
                return (
                  (this.Sa[m] = Be),
                  (this.Sa[T] = Re),
                  this.handleError(
                    gn(this.db, m, W.length - 1, 1, 0, 0, Be, Re, 0)
                  ),
                  this
                );
              }),
              (d.prototype.vc = function (m) {
                return (
                  this.fb &&
                    (bn(this.db, 0, 0), Ge(this.fb), (this.fb = void 0)),
                  m
                    ? ((this.fb = kt(function (T, L, N, W, ee) {
                        switch (L) {
                          case 18:
                            T = "insert";
                            break;
                          case 23:
                            T = "update";
                            break;
                          case 9:
                            T = "delete";
                            break;
                          default:
                            throw (
                              "unknown operationCode in updateHook callback: " +
                              L
                            );
                        }
                        if (
                          ((N = j(N)), (W = j(W)), ee > Number.MAX_SAFE_INTEGER)
                        )
                          throw "rowId too big to fit inside a Number";
                        m(T, N, W, Number(ee));
                      }, "viiiij")),
                      bn(this.db, this.fb, 0),
                      this)
                    : this
                );
              }),
              (s.prototype.bind = s.prototype.bind),
              (s.prototype.step = s.prototype.step),
              (s.prototype.get = s.prototype.get),
              (s.prototype.getColumnNames = s.prototype.Db),
              (s.prototype.getAsObject = s.prototype.Ob),
              (s.prototype.getSQL = s.prototype.lc),
              (s.prototype.getNormalizedSQL = s.prototype.ic),
              (s.prototype.run = s.prototype.Jb),
              (s.prototype.reset = s.prototype.reset),
              (s.prototype.freemem = s.prototype.Cb),
              (s.prototype.free = s.prototype.cb),
              (o.prototype.next = o.prototype.next),
              (o.prototype.getRemainingSQL = o.prototype.jc),
              (d.prototype.run = d.prototype.Jb),
              (d.prototype.exec = d.prototype.exec),
              (d.prototype.each = d.prototype.ec),
              (d.prototype.prepare = d.prototype.Gb),
              (d.prototype.iterateStatements = d.prototype.pc),
              (d.prototype.export = d.prototype.fc),
              (d.prototype.close = d.prototype.close),
              (d.prototype.handleError = d.prototype.handleError),
              (d.prototype.getRowsModified = d.prototype.kc),
              (d.prototype.create_function = d.prototype.bc),
              (d.prototype.create_aggregate = d.prototype.ac),
              (d.prototype.updateHook = d.prototype.vc),
              (a.Database = d));
          };
          var u = "./this.program",
            p =
              (pn =
                (cn = globalThis.document) == null
                  ? void 0
                  : cn.currentScript) == null
                ? void 0
                : pn.src;
          l && (p = self.location.href);
          var h = "",
            b,
            k;
          if (c || l) {
            try {
              h = new URL(".", p).href;
            } catch (e) {}
            (l &&
              (k = (e) => {
                var t = new XMLHttpRequest();
                return (
                  t.open("GET", e, !1),
                  (t.responseType = "arraybuffer"),
                  t.send(null),
                  new Uint8Array(t.response)
                );
              }),
              (b = async (e) => {
                if (
                  ((e = await fetch(e, { credentials: "same-origin" })), e.ok)
                )
                  return e.arrayBuffer();
                throw Error(e.status + " : " + e.url);
              }));
          }
          var g = console.log.bind(console),
            x = console.error.bind(console),
            C,
            R = !1,
            S,
            F,
            B,
            A,
            v,
            w,
            O,
            M,
            I;
          function J() {
            var e = Wt.buffer;
            ((F = new Int8Array(e)),
              (A = new Int16Array(e)),
              (B = new Uint8Array(e)),
              new Uint16Array(e),
              (v = new Int32Array(e)),
              (w = new Uint32Array(e)),
              (O = new Float32Array(e)),
              (M = new Float64Array(e)),
              (I = new BigInt64Array(e)),
              new BigUint64Array(e));
          }
          function q(e) {
            var t;
            throw (
              (t = a.onAbort) == null || t.call(a, e),
              (e = "Aborted(" + e + ")"),
              x(e),
              (R = !0),
              new WebAssembly.RuntimeError(
                e + ". Build with -sASSERTIONS for more info."
              )
            );
          }
          var te;
          async function se(e) {
            if (!C)
              try {
                var t = await b(e);
                return new Uint8Array(t);
              } catch (s) {}
            if (e == te && C) e = new Uint8Array(C);
            else if (k) e = k(e);
            else throw "both async and sync fetching of the wasm failed";
            return e;
          }
          async function G(e, t) {
            try {
              var s = await se(e);
              return await WebAssembly.instantiate(s, t);
            } catch (o) {
              (x(`failed to asynchronously prepare wasm: ${o}`), q(o));
            }
          }
          async function ye(e) {
            var t = te;
            if (!C)
              try {
                var s = fetch(t, { credentials: "same-origin" });
                return await WebAssembly.instantiateStreaming(s, e);
              } catch (o) {
                (x(`wasm streaming compile failed: ${o}`),
                  x("falling back to ArrayBuffer instantiation"));
              }
            return G(t, e);
          }
          class ue {
            constructor(t) {
              Xe(this, "name", "ExitStatus");
              ((this.message = `Program terminated with exit(${t})`),
                (this.status = t));
            }
          }
          var V = (e) => {
              for (; 0 < e.length; ) e.shift()(a);
            },
            U = [],
            be = [],
            we = () => {
              var e = a.preRun.shift();
              be.push(e);
            },
            ge = 0,
            Ce = null;
          function fe(e, t = "i8") {
            switch ((t.endsWith("*") && (t = "*"), t)) {
              case "i1":
                return F[e];
              case "i8":
                return F[e];
              case "i16":
                return A[e >> 1];
              case "i32":
                return v[e >> 2];
              case "i64":
                return I[e >> 3];
              case "float":
                return O[e >> 2];
              case "double":
                return M[e >> 3];
              case "*":
                return w[e >> 2];
              default:
                q(`invalid type for getValue: ${t}`);
            }
          }
          var Le = !0;
          function De(e) {
            var t = "i32";
            switch ((t.endsWith("*") && (t = "*"), t)) {
              case "i1":
                F[e] = 0;
                break;
              case "i8":
                F[e] = 0;
                break;
              case "i16":
                A[e >> 1] = 0;
                break;
              case "i32":
                v[e >> 2] = 0;
                break;
              case "i64":
                I[e >> 3] = BigInt(0);
                break;
              case "float":
                O[e >> 2] = 0;
                break;
              case "double":
                M[e >> 3] = 0;
                break;
              case "*":
                w[e >> 2] = 0;
                break;
              default:
                q(`invalid type for setValue: ${t}`);
            }
          }
          var Ie = new TextDecoder(),
            K = (e, t, s, o) => {
              if (((s = t + s), o)) return s;
              for (; e[t] && !(t >= s); ) ++t;
              return t;
            },
            j = (e, t, s) => (e ? Ie.decode(B.subarray(e, K(B, e, t, s))) : ""),
            ke = (e, t) => {
              for (var s = 0, o = e.length - 1; 0 <= o; o--) {
                var d = e[o];
                d === "."
                  ? e.splice(o, 1)
                  : d === ".."
                    ? (e.splice(o, 1), s++)
                    : s && (e.splice(o, 1), s--);
              }
              if (t) for (; s; s--) e.unshift("..");
              return e;
            },
            ce = (e) => {
              var t = e.charAt(0) === "/",
                s = e.slice(-1) === "/";
              return (
                (e = ke(
                  e.split("/").filter((o) => !!o),
                  !t
                ).join("/")) ||
                  t ||
                  (e = "."),
                e && s && (e += "/"),
                (t ? "/" : "") + e
              );
            },
            Ae = (e) => {
              var t =
                /^(\/?|)([\s\S]*?)((?:\.{1,2}|[^\/]+?|)(\.[^.\/]*|))(?:[\/]*)$/
                  .exec(e)
                  .slice(1);
              return (
                (e = t[0]),
                (t = t[1]),
                !e && !t ? "." : (t && (t = t.slice(0, -1)), e + t)
              );
            },
            Ne = (e) => e && e.match(/([^\/]+|\/)\/*$/)[1],
            vt = () => (e) => crypto.getRandomValues(e),
            Lr = (e) => {
              (Lr = vt())(e);
            },
            Xn = (...e) => {
              for (var t = "", s = !1, o = e.length - 1; -1 <= o && !s; o--) {
                if (((s = 0 <= o ? e[o] : "/"), typeof s != "string"))
                  throw new TypeError(
                    "Arguments to path.resolve must be strings"
                  );
                if (!s) return "";
                ((t = s + "/" + t), (s = s.charAt(0) === "/"));
              }
              return (
                (t = ke(
                  t.split("/").filter((d) => !!d),
                  !s
                ).join("/")),
                (s ? "/" : "") + t || "."
              );
            },
            Et = (e) => {
              var t = K(e, 0);
              return Ie.decode(
                e.buffer ? e.subarray(0, t) : new Uint8Array(e.slice(0, t))
              );
            },
            ir = [],
            pt = (e) => {
              for (var t = 0, s = 0; s < e.length; ++s) {
                var o = e.charCodeAt(s);
                127 >= o
                  ? t++
                  : 2047 >= o
                    ? (t += 2)
                    : 55296 <= o && 57343 >= o
                      ? ((t += 4), ++s)
                      : (t += 3);
              }
              return t;
            },
            je = (e, t, s, o) => {
              if (!(0 < o)) return 0;
              var d = s;
              o = s + o - 1;
              for (var E = 0; E < e.length; ++E) {
                var P = e.codePointAt(E);
                if (127 >= P) {
                  if (s >= o) break;
                  t[s++] = P;
                } else if (2047 >= P) {
                  if (s + 1 >= o) break;
                  ((t[s++] = 192 | (P >> 6)), (t[s++] = 128 | (P & 63)));
                } else if (65535 >= P) {
                  if (s + 2 >= o) break;
                  ((t[s++] = 224 | (P >> 12)),
                    (t[s++] = 128 | ((P >> 6) & 63)),
                    (t[s++] = 128 | (P & 63)));
                } else {
                  if (s + 3 >= o) break;
                  ((t[s++] = 240 | (P >> 18)),
                    (t[s++] = 128 | ((P >> 12) & 63)),
                    (t[s++] = 128 | ((P >> 6) & 63)),
                    (t[s++] = 128 | (P & 63)),
                    E++);
                }
              }
              return ((t[s] = 0), s - d);
            },
            Ir = [];
          function Nr(e, t) {
            ((Ir[e] = { input: [], output: [], kb: t }), dr(e, Yn));
          }
          var Yn = {
              open(e) {
                var t = Ir[e.node.nb];
                if (!t) throw new D(43);
                ((e.Va = t), (e.seekable = !1));
              },
              close(e) {
                e.Va.kb.lb(e.Va);
              },
              lb(e) {
                e.Va.kb.lb(e.Va);
              },
              read(e, t, s, o) {
                if (!e.Va || !e.Va.kb.Qb) throw new D(60);
                for (var d = 0, E = 0; E < o; E++) {
                  try {
                    var P = e.Va.kb.Qb(e.Va);
                  } catch ($) {
                    throw new D(29);
                  }
                  if (P === void 0 && d === 0) throw new D(6);
                  if (P == null) break;
                  (d++, (t[s + E] = P));
                }
                return (d && (e.node.$a = Date.now()), d);
              },
              write(e, t, s, o) {
                if (!e.Va || !e.Va.kb.Hb) throw new D(60);
                try {
                  for (var d = 0; d < o; d++) e.Va.kb.Hb(e.Va, t[s + d]);
                } catch (E) {
                  throw new D(29);
                }
                return (o && (e.node.Ua = e.node.Ta = Date.now()), d);
              },
            },
            es = {
              Qb() {
                var s;
                e: {
                  if (!ir.length) {
                    var e = null;
                    if (
                      ((s = globalThis.window) != null &&
                        s.prompt &&
                        ((e = window.prompt("Input: ")),
                        e !== null &&
                          (e += `
`)),
                      !e)
                    ) {
                      var t = null;
                      break e;
                    }
                    ((t = Array(pt(e) + 1)),
                      (e = je(e, t, 0, t.length)),
                      (t.length = e),
                      (ir = t));
                  }
                  t = ir.shift();
                }
                return t;
              },
              Hb(e, t) {
                t === null || t === 10
                  ? (g(Et(e.output)), (e.output = []))
                  : t != 0 && e.output.push(t);
              },
              lb(e) {
                var t;
                0 < ((t = e.output) == null ? void 0 : t.length) &&
                  (g(Et(e.output)), (e.output = []));
              },
              Dc() {
                return {
                  yc: 25856,
                  Ac: 5,
                  xc: 191,
                  zc: 35387,
                  wc: [
                    3, 28, 127, 21, 4, 0, 1, 0, 17, 19, 26, 0, 18, 15, 23, 22,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  ],
                };
              },
              Ec() {
                return 0;
              },
              Fc() {
                return [24, 80];
              },
            },
            ts = {
              Hb(e, t) {
                t === null || t === 10
                  ? (x(Et(e.output)), (e.output = []))
                  : t != 0 && e.output.push(t);
              },
              lb(e) {
                var t;
                0 < ((t = e.output) == null ? void 0 : t.length) &&
                  (x(Et(e.output)), (e.output = []));
              },
            },
            H = {
              Za: null,
              ab() {
                return H.createNode(null, "/", 16895, 0);
              },
              createNode(e, t, s, o) {
                if ((s & 61440) === 24576 || (s & 61440) === 4096)
                  throw new D(63);
                return (
                  H.Za ||
                    (H.Za = {
                      dir: {
                        node: {
                          Wa: H.La.Wa,
                          Xa: H.La.Xa,
                          mb: H.La.mb,
                          rb: H.La.rb,
                          Tb: H.La.Tb,
                          xb: H.La.xb,
                          vb: H.La.vb,
                          Ib: H.La.Ib,
                          wb: H.La.wb,
                        },
                        stream: { Ya: H.Ma.Ya },
                      },
                      file: {
                        node: { Wa: H.La.Wa, Xa: H.La.Xa },
                        stream: {
                          Ya: H.Ma.Ya,
                          read: H.Ma.read,
                          write: H.Ma.write,
                          sb: H.Ma.sb,
                          tb: H.Ma.tb,
                        },
                      },
                      link: {
                        node: { Wa: H.La.Wa, Xa: H.La.Xa, eb: H.La.eb },
                        stream: {},
                      },
                      Nb: { node: { Wa: H.La.Wa, Xa: H.La.Xa }, stream: is },
                    }),
                  (s = qr(e, t, s, o)),
                  Ee(s.mode)
                    ? ((s.La = H.Za.dir.node),
                      (s.Ma = H.Za.dir.stream),
                      (s.Na = {}))
                    : (s.mode & 61440) === 32768
                      ? ((s.La = H.Za.file.node),
                        (s.Ma = H.Za.file.stream),
                        (s.Ra = 0),
                        (s.Na = null))
                      : (s.mode & 61440) === 40960
                        ? ((s.La = H.Za.link.node), (s.Ma = H.Za.link.stream))
                        : (s.mode & 61440) === 8192 &&
                          ((s.La = H.Za.Nb.node), (s.Ma = H.Za.Nb.stream)),
                  (s.$a = s.Ua = s.Ta = Date.now()),
                  e && ((e.Na[t] = s), (e.$a = e.Ua = e.Ta = s.$a)),
                  s
                );
              },
              Cc(e) {
                return e.Na
                  ? e.Na.subarray
                    ? e.Na.subarray(0, e.Ra)
                    : new Uint8Array(e.Na)
                  : new Uint8Array(0);
              },
              La: {
                Wa(e) {
                  var t = {};
                  return (
                    (t.cc = (e.mode & 61440) === 8192 ? e.id : 1),
                    (t.oc = e.id),
                    (t.mode = e.mode),
                    (t.rc = 1),
                    (t.uid = 0),
                    (t.nc = 0),
                    (t.nb = e.nb),
                    Ee(e.mode)
                      ? (t.size = 4096)
                      : (e.mode & 61440) === 32768
                        ? (t.size = e.Ra)
                        : (e.mode & 61440) === 40960
                          ? (t.size = e.link.length)
                          : (t.size = 0),
                    (t.$a = new Date(e.$a)),
                    (t.Ua = new Date(e.Ua)),
                    (t.Ta = new Date(e.Ta)),
                    (t.Zb = 4096),
                    (t.$b = Math.ceil(t.size / t.Zb)),
                    t
                  );
                },
                Xa(e, t) {
                  for (var s of ["mode", "atime", "mtime", "ctime"])
                    t[s] != null && (e[s] = t[s]);
                  t.size !== void 0 &&
                    ((t = t.size),
                    e.Ra != t &&
                      (t == 0
                        ? ((e.Na = null), (e.Ra = 0))
                        : ((s = e.Na),
                          (e.Na = new Uint8Array(t)),
                          s && e.Na.set(s.subarray(0, Math.min(t, e.Ra))),
                          (e.Ra = t))));
                },
                mb() {
                  throw (
                    H.zb ||
                      ((H.zb = new D(44)),
                      (H.zb.stack = "<generic error, no stack>")),
                    H.zb
                  );
                },
                rb(e, t, s, o) {
                  return H.createNode(e, t, s, o);
                },
                Tb(e, t, s) {
                  try {
                    var o = tt(t, s);
                  } catch (E) {}
                  if (o) {
                    if (Ee(e.mode)) for (var d in o.Na) throw new D(55);
                    pr(o);
                  }
                  (delete e.parent.Na[e.name],
                    (t.Na[s] = e),
                    (e.name = s),
                    (t.Ta = t.Ua = e.parent.Ta = e.parent.Ua = Date.now()));
                },
                xb(e, t) {
                  (delete e.Na[t], (e.Ta = e.Ua = Date.now()));
                },
                vb(e, t) {
                  var s = tt(e, t),
                    o;
                  for (o in s.Na) throw new D(55);
                  (delete e.Na[t], (e.Ta = e.Ua = Date.now()));
                },
                Ib(e) {
                  return [".", "..", ...Object.keys(e.Na)];
                },
                wb(e, t, s) {
                  return ((e = H.createNode(e, t, 41471, 0)), (e.link = s), e);
                },
                eb(e) {
                  if ((e.mode & 61440) !== 40960) throw new D(28);
                  return e.link;
                },
              },
              Ma: {
                read(e, t, s, o, d) {
                  var E = e.node.Na;
                  if (d >= e.node.Ra) return 0;
                  if (((e = Math.min(e.node.Ra - d, o)), 8 < e && E.subarray))
                    t.set(E.subarray(d, d + e), s);
                  else for (o = 0; o < e; o++) t[s + o] = E[d + o];
                  return e;
                },
                write(e, t, s, o, d, E) {
                  if ((t.buffer === F.buffer && (E = !1), !o)) return 0;
                  if (
                    ((e = e.node),
                    (e.Ua = e.Ta = Date.now()),
                    t.subarray && (!e.Na || e.Na.subarray))
                  ) {
                    if (E) return ((e.Na = t.subarray(s, s + o)), (e.Ra = o));
                    if (e.Ra === 0 && d === 0)
                      return ((e.Na = t.slice(s, s + o)), (e.Ra = o));
                    if (d + o <= e.Ra)
                      return (e.Na.set(t.subarray(s, s + o), d), o);
                  }
                  E = d + o;
                  var P = e.Na ? e.Na.length : 0;
                  if (
                    (P >= E ||
                      ((E = Math.max(E, (P * (1048576 > P ? 2 : 1.125)) >>> 0)),
                      P != 0 && (E = Math.max(E, 256)),
                      (P = e.Na),
                      (e.Na = new Uint8Array(E)),
                      0 < e.Ra && e.Na.set(P.subarray(0, e.Ra), 0)),
                    e.Na.subarray && t.subarray)
                  )
                    e.Na.set(t.subarray(s, s + o), d);
                  else for (E = 0; E < o; E++) e.Na[d + E] = t[s + E];
                  return ((e.Ra = Math.max(e.Ra, d + o)), o);
                },
                Ya(e, t, s) {
                  if (
                    (s === 1
                      ? (t += e.position)
                      : s === 2 &&
                        (e.node.mode & 61440) === 32768 &&
                        (t += e.node.Ra),
                    0 > t)
                  )
                    throw new D(28);
                  return t;
                },
                sb(e, t, s, o, d) {
                  if ((e.node.mode & 61440) !== 32768) throw new D(43);
                  if (((e = e.node.Na), d & 2 || !e || e.buffer !== F.buffer)) {
                    ((d = !0), (o = 65536 * Math.ceil(t / 65536)));
                    var E = on(65536, o);
                    if ((E && B.fill(0, E, E + o), (o = E), !o))
                      throw new D(48);
                    e &&
                      ((0 < s || s + t < e.length) &&
                        (e.subarray
                          ? (e = e.subarray(s, s + t))
                          : (e = Array.prototype.slice.call(e, s, s + t))),
                      F.set(e, o));
                  } else ((d = !1), (o = e.byteOffset));
                  return { tc: o, Ub: d };
                },
                tb(e, t, s, o) {
                  return (H.Ma.write(e, t, 0, o, s, !1), 0);
                },
              },
            },
            jr = (e, t) => {
              var s = 0;
              return (e && (s |= 365), t && (s |= 146), s);
            },
            or = null,
            zr = {},
            ut = [],
            rs = 1,
            Ze = null,
            $r = !1,
            Vr = !0,
            D = class {
              constructor(e) {
                Xe(this, "name", "ErrnoError");
                this.Pa = e;
              }
            },
            ns = class {
              constructor() {
                Xe(this, "qb", {});
                Xe(this, "node", null);
              }
              get flags() {
                return this.qb.flags;
              }
              set flags(e) {
                this.qb.flags = e;
              }
              get position() {
                return this.qb.position;
              }
              set position(e) {
                this.qb.position = e;
              }
            },
            ss = class {
              constructor(e, t, s, o) {
                Xe(this, "La", {});
                Xe(this, "Ma", {});
                Xe(this, "ib", null);
                (e || (e = this),
                  (this.parent = e),
                  (this.ab = e.ab),
                  (this.id = rs++),
                  (this.name = t),
                  (this.mode = s),
                  (this.nb = o),
                  (this.$a = this.Ua = this.Ta = Date.now()));
              }
              get read() {
                return (this.mode & 365) === 365;
              }
              set read(e) {
                e ? (this.mode |= 365) : (this.mode &= -366);
              }
              get write() {
                return (this.mode & 146) === 146;
              }
              set write(e) {
                e ? (this.mode |= 146) : (this.mode &= -147);
              }
            };
          function Fe(e, t = {}) {
            var $;
            if (!e) throw new D(44);
            (($ = t.Bb) != null || (t.Bb = !0),
              e.charAt(0) === "/" || (e = "//" + e));
            var s = 0;
            e: for (; 40 > s; s++) {
              e = e.split("/").filter((Q) => !!Q);
              for (var o = or, d = "/", E = 0; E < e.length; E++) {
                var P = E === e.length - 1;
                if (P && t.parent) break;
                if (e[E] !== ".")
                  if (e[E] === "..")
                    if (((d = Ae(d)), o === o.parent)) {
                      ((e = d + "/" + e.slice(E + 1).join("/")), s--);
                      continue e;
                    } else o = o.parent;
                  else {
                    d = ce(d + "/" + e[E]);
                    try {
                      o = tt(o, e[E]);
                    } catch (Q) {
                      if ((Q == null ? void 0 : Q.Pa) === 44 && P && t.sc)
                        return { path: d };
                      throw Q;
                    }
                    if (
                      (!o.ib || (P && !t.Bb) || (o = o.ib.root),
                      (o.mode & 61440) === 40960 && (!P || t.hb))
                    ) {
                      if (!o.La.eb) throw new D(52);
                      ((o = o.La.eb(o)),
                        o.charAt(0) === "/" || (o = Ae(d) + "/" + o),
                        (e = o + "/" + e.slice(E + 1).join("/")));
                      continue e;
                    }
                  }
              }
              return { path: d, node: o };
            }
            throw new D(32);
          }
          function lr(e) {
            for (var t; ; ) {
              if (e === e.parent)
                return (
                  (e = e.ab.Sb),
                  t ? (e[e.length - 1] !== "/" ? `${e}/${t}` : e + t) : e
                );
              ((t = t ? `${e.name}/${t}` : e.name), (e = e.parent));
            }
          }
          function cr(e, t) {
            for (var s = 0, o = 0; o < t.length; o++)
              s = ((s << 5) - s + t.charCodeAt(o)) | 0;
            return ((e + s) >>> 0) % Ze.length;
          }
          function pr(e) {
            var t = cr(e.parent.id, e.name);
            if (Ze[t] === e) Ze[t] = e.jb;
            else
              for (t = Ze[t]; t; ) {
                if (t.jb === e) {
                  t.jb = e.jb;
                  break;
                }
                t = t.jb;
              }
          }
          function tt(e, t) {
            var s = Ee(e.mode) ? ((s = dt(e, "x")) ? s : e.La.mb ? 0 : 2) : 54;
            if (s) throw new D(s);
            for (s = Ze[cr(e.id, t)]; s; s = s.jb) {
              var o = s.name;
              if (s.parent.id === e.id && o === t) return s;
            }
            return e.La.mb(e, t);
          }
          function qr(e, t, s, o) {
            return (
              (e = new ss(e, t, s, o)),
              (t = cr(e.parent.id, e.name)),
              (e.jb = Ze[t]),
              (Ze[t] = e)
            );
          }
          function Ee(e) {
            return (e & 61440) === 16384;
          }
          function dt(e, t) {
            return Vr
              ? 0
              : (t.includes("r") && !(e.mode & 292)) ||
                  (t.includes("w") && !(e.mode & 146)) ||
                  (t.includes("x") && !(e.mode & 73))
                ? 2
                : 0;
          }
          function Hr(e, t) {
            if (!Ee(e.mode)) return 54;
            try {
              return (tt(e, t), 20);
            } catch (s) {}
            return dt(e, "wx");
          }
          function Kr(e, t, s) {
            try {
              var o = tt(e, t);
            } catch (d) {
              return d.Pa;
            }
            if ((e = dt(e, "wx"))) return e;
            if (s) {
              if (!Ee(o.mode)) return 54;
              if (o === o.parent || lr(o) === "/") return 10;
            } else if (Ee(o.mode)) return 31;
            return 0;
          }
          function Lt(e) {
            if (!e) throw new D(63);
            return e;
          }
          function ve(e) {
            if (((e = ut[e]), !e)) throw new D(8);
            return e;
          }
          function Ur(e, t = -1) {
            if (((e = Object.assign(new ns(), e)), t == -1))
              e: {
                for (t = 0; 4096 >= t; t++) if (!ut[t]) break e;
                throw new D(33);
              }
            return ((e.bb = t), (ut[t] = e));
          }
          function as(e, t = -1) {
            var s, o;
            return (
              (e = Ur(e, t)),
              (o = (s = e.Ma) == null ? void 0 : s.Bc) == null || o.call(s, e),
              e
            );
          }
          function ur(e, t, s) {
            var o = e == null ? void 0 : e.Ma.Xa;
            ((e = o ? e : t), o != null || (o = t.La.Xa), Lt(o), o(e, s));
          }
          var is = {
            open(e) {
              var t, s;
              ((e.Ma = zr[e.node.nb].Ma),
                (s = (t = e.Ma).open) == null || s.call(t, e));
            },
            Ya() {
              throw new D(70);
            },
          };
          function dr(e, t) {
            zr[e] = { Ma: t };
          }
          function Wr(e, t) {
            var s = t === "/";
            if (s && or) throw new D(10);
            if (!s && t) {
              var o = Fe(t, { Bb: !1 });
              if (((t = o.path), (o = o.node), o.ib)) throw new D(10);
              if (!Ee(o.mode)) throw new D(54);
            }
            ((t = { type: e, Gc: {}, Sb: t, qc: [] }),
              (e = e.ab(t)),
              (e.ab = t),
              (t.root = e),
              s ? (or = e) : o && ((o.ib = t), o.ab && o.ab.qc.push(t)));
          }
          function It(e, t, s) {
            var o = Fe(e, { parent: !0 }).node;
            if (((e = Ne(e)), !e)) throw new D(28);
            if (e === "." || e === "..") throw new D(20);
            var d = Hr(o, e);
            if (d) throw new D(d);
            if (!o.La.rb) throw new D(63);
            return o.La.rb(o, e, t, s);
          }
          function os(e, t = 438) {
            return It(e, (t & 4095) | 32768, 0);
          }
          function ze(e, t = 511) {
            return It(e, (t & 1023) | 16384, 0);
          }
          function Nt(e, t, s) {
            (typeof s == "undefined" && ((s = t), (t = 438)),
              It(e, t | 8192, s));
          }
          function fr(e, t) {
            if (!Xn(e)) throw new D(44);
            var s = Fe(t, { parent: !0 }).node;
            if (!s) throw new D(44);
            t = Ne(t);
            var o = Hr(s, t);
            if (o) throw new D(o);
            if (!s.La.wb) throw new D(63);
            s.La.wb(s, t, e);
          }
          function Zr(e) {
            var t = Fe(e, { parent: !0 }).node;
            e = Ne(e);
            var s = tt(t, e),
              o = Kr(t, e, !0);
            if (o) throw new D(o);
            if (!t.La.vb) throw new D(63);
            if (s.ib) throw new D(10);
            (t.La.vb(t, e), pr(s));
          }
          function Jr(e) {
            var t = Fe(e, { parent: !0 }).node;
            if (!t) throw new D(44);
            e = Ne(e);
            var s = tt(t, e),
              o = Kr(t, e, !1);
            if (o) throw new D(o);
            if (!t.La.xb) throw new D(63);
            if (s.ib) throw new D(10);
            (t.La.xb(t, e), pr(s));
          }
          function xt(e, t) {
            return ((e = Fe(e, { hb: !t }).node), Lt(e.La.Wa)(e));
          }
          function Gr(e, t, s, o) {
            ur(e, t, {
              mode: (s & 4095) | (t.mode & -4096),
              Ta: Date.now(),
              dc: o,
            });
          }
          function jt(e, t) {
            ((e = typeof e == "string" ? Fe(e, { hb: !0 }).node : e),
              Gr(null, e, t));
          }
          function Qr(e, t, s) {
            if (Ee(t.mode)) throw new D(31);
            if ((t.mode & 61440) !== 32768) throw new D(28);
            var o = dt(t, "w");
            if (o) throw new D(o);
            ur(e, t, { size: s, timestamp: Date.now() });
          }
          function ft(e, t, s = 438) {
            if (e === "") throw new D(44);
            if (typeof t == "string") {
              var o = { r: 0, "r+": 2, w: 577, "w+": 578, a: 1089, "a+": 1090 }[
                t
              ];
              if (typeof o == "undefined")
                throw Error(`Unknown file open mode: ${t}`);
              t = o;
            }
            if (((s = t & 64 ? (s & 4095) | 32768 : 0), typeof e == "object"))
              o = e;
            else {
              var d = e.endsWith("/"),
                E = Fe(e, { hb: !(t & 131072), sc: !0 });
              ((o = E.node), (e = E.path));
            }
            if (((E = !1), t & 64))
              if (o) {
                if (t & 128) throw new D(20);
              } else {
                if (d) throw new D(31);
                ((o = It(e, s | 511, 0)), (E = !0));
              }
            if (!o) throw new D(44);
            if (
              ((o.mode & 61440) === 8192 && (t &= -513),
              t & 65536 && !Ee(o.mode))
            )
              throw new D(54);
            if (
              !E &&
              (o
                ? (o.mode & 61440) === 40960
                  ? (d = 32)
                  : ((d = ["r", "w", "rw"][t & 3]),
                    t & 512 && (d += "w"),
                    (d = Ee(o.mode) && (d !== "r" || t & 576) ? 31 : dt(o, d)))
                : (d = 44),
              d)
            )
              throw new D(d);
            return (
              t & 512 &&
                !E &&
                ((d = o),
                (d = typeof d == "string" ? Fe(d, { hb: !0 }).node : d),
                Qr(null, d, 0)),
              (t = Ur({
                node: o,
                path: lr(o),
                flags: t & -131713,
                seekable: !0,
                position: 0,
                Ma: o.Ma,
                uc: [],
                error: !1,
              })),
              t.Ma.open && t.Ma.open(t),
              E && jt(o, s & 511),
              t
            );
          }
          function hr(e) {
            if (e.bb === null) throw new D(8);
            e.Eb && (e.Eb = null);
            try {
              e.Ma.close && e.Ma.close(e);
            } catch (t) {
              throw t;
            } finally {
              ut[e.bb] = null;
            }
            e.bb = null;
          }
          function Xr(e, t, s) {
            if (e.bb === null) throw new D(8);
            if (!e.seekable || !e.Ma.Ya) throw new D(70);
            if (s != 0 && s != 1 && s != 2) throw new D(28);
            ((e.position = e.Ma.Ya(e, t, s)), (e.uc = []));
          }
          function Yr(e, t, s, o, d) {
            if (0 > o || 0 > d) throw new D(28);
            if (e.bb === null) throw new D(8);
            if ((e.flags & 2097155) === 1) throw new D(8);
            if (Ee(e.node.mode)) throw new D(31);
            if (!e.Ma.read) throw new D(28);
            var E = typeof d != "undefined";
            if (!E) d = e.position;
            else if (!e.seekable) throw new D(70);
            return ((t = e.Ma.read(e, t, s, o, d)), E || (e.position += t), t);
          }
          function en(e, t, s, o, d) {
            if (0 > o || 0 > d) throw new D(28);
            if (e.bb === null) throw new D(8);
            if ((e.flags & 2097155) === 0) throw new D(8);
            if (Ee(e.node.mode)) throw new D(31);
            if (!e.Ma.write) throw new D(28);
            e.seekable && e.flags & 1024 && Xr(e, 0, 2);
            var E = typeof d != "undefined";
            if (!E) d = e.position;
            else if (!e.seekable) throw new D(70);
            return (
              (t = e.Ma.write(e, t, s, o, d, void 0)),
              E || (e.position += t),
              t
            );
          }
          function ls(e) {
            var t = t || 0,
              s = "binary";
            (s !== "utf8" &&
              s !== "binary" &&
              q(`Invalid encoding type "${s}"`),
              (t = ft(e, t)),
              (e = xt(e).size));
            var o = new Uint8Array(e);
            return (Yr(t, o, 0, e, 0), s === "utf8" && (o = Et(o)), hr(t), o);
          }
          function Je(e, t, s) {
            var E;
            e = ce("/dev/" + e);
            var o = jr(!!t, !!s);
            (E = Je.Rb) != null || (Je.Rb = 64);
            var d = (Je.Rb++ << 8) | 0;
            (dr(d, {
              open(P) {
                P.seekable = !1;
              },
              close() {
                var P;
                (P = s == null ? void 0 : s.buffer) != null &&
                  P.length &&
                  s(10);
              },
              read(P, $, Q, Z) {
                for (var Y = 0, _e = 0; _e < Z; _e++) {
                  try {
                    var ht = t();
                  } catch (un) {
                    throw new D(29);
                  }
                  if (ht === void 0 && Y === 0) throw new D(6);
                  if (ht == null) break;
                  (Y++, ($[Q + _e] = ht));
                }
                return (Y && (P.node.$a = Date.now()), Y);
              },
              write(P, $, Q, Z) {
                for (var Y = 0; Y < Z; Y++)
                  try {
                    s($[Q + Y]);
                  } catch (_e) {
                    throw new D(29);
                  }
                return (Z && (P.node.Ua = P.node.Ta = Date.now()), Y);
              },
            }),
              Nt(e, o, d));
          }
          var ne = {};
          function rt(e, t, s) {
            if (t.charAt(0) === "/") return t;
            if (((e = e === -100 ? "/" : ve(e).path), t.length == 0)) {
              if (!s) throw new D(44);
              return e;
            }
            return e + "/" + t;
          }
          function zt(e, t) {
            ((w[e >> 2] = t.cc),
              (w[(e + 4) >> 2] = t.mode),
              (w[(e + 8) >> 2] = t.rc),
              (w[(e + 12) >> 2] = t.uid),
              (w[(e + 16) >> 2] = t.nc),
              (w[(e + 20) >> 2] = t.nb),
              (I[(e + 24) >> 3] = BigInt(t.size)),
              (v[(e + 32) >> 2] = 4096),
              (v[(e + 36) >> 2] = t.$b));
            var s = t.$a.getTime(),
              o = t.Ua.getTime(),
              d = t.Ta.getTime();
            return (
              (I[(e + 40) >> 3] = BigInt(Math.floor(s / 1e3))),
              (w[(e + 48) >> 2] = (s % 1e3) * 1e6),
              (I[(e + 56) >> 3] = BigInt(Math.floor(o / 1e3))),
              (w[(e + 64) >> 2] = (o % 1e3) * 1e6),
              (I[(e + 72) >> 3] = BigInt(Math.floor(d / 1e3))),
              (w[(e + 80) >> 2] = (d % 1e3) * 1e6),
              (I[(e + 88) >> 3] = BigInt(t.oc)),
              0
            );
          }
          var $t = void 0,
            Vt = () => {
              var e = v[+$t >> 2];
              return (($t += 4), e);
            },
            gr = 0,
            cs = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
            ps = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
            wt = {},
            tn = (e) => {
              if (!(e instanceof ue || e == "unwind")) throw e;
            },
            rn = (e) => {
              var t;
              throw (
                (S = e),
                Le ||
                  0 < gr ||
                  ((t = a.onExit) == null || t.call(a, e), (R = !0)),
                new ue(e)
              );
            },
            us = (e) => {
              if (!R)
                try {
                  e();
                } catch (t) {
                  tn(t);
                } finally {
                  if (!(Le || 0 < gr))
                    try {
                      ((S = e = S), rn(e));
                    } catch (t) {
                      tn(t);
                    }
                }
            },
            _r = {},
            nn = () => {
              var o, d;
              if (!mr) {
                var e = {
                    USER: "web_user",
                    LOGNAME: "web_user",
                    PATH: "/",
                    PWD: "/",
                    HOME: "/home/web_user",
                    LANG:
                      ((d =
                        (o = globalThis.navigator) == null
                          ? void 0
                          : o.language) != null
                        ? d
                        : "C"
                      ).replace("-", "_") + ".UTF-8",
                    _: u || "./this.program",
                  },
                  t;
                for (t in _r) _r[t] === void 0 ? delete e[t] : (e[t] = _r[t]);
                var s = [];
                for (t in e) s.push(`${t}=${e[t]}`);
                mr = s;
              }
              return mr;
            },
            mr,
            ds = (e, t, s, o) => {
              var d = {
                string: (Z) => {
                  var Y = 0;
                  if (Z != null && Z !== 0) {
                    Y = pt(Z) + 1;
                    var _e = st(Y);
                    (je(Z, B, _e, Y), (Y = _e));
                  }
                  return Y;
                },
                array: (Z) => {
                  var Y = st(Z.length);
                  return (F.set(Z, Y), Y);
                },
              };
              e = a["_" + e];
              var E = [],
                P = 0;
              if (o)
                for (var $ = 0; $ < o.length; $++) {
                  var Q = d[s[$]];
                  Q ? (P === 0 && (P = Ut()), (E[$] = Q(o[$]))) : (E[$] = o[$]);
                }
              return (
                (s = e(...E)),
                (s = (function (Z) {
                  return (
                    P !== 0 && Kt(P),
                    t === "string" ? j(Z) : t === "boolean" ? !!Z : Z
                  );
                })(s))
              );
            },
            qt = (e) => {
              var t = pt(e) + 1,
                s = Ht(t);
              return (s && je(e, B, s, t), s);
            },
            nt,
            yr = [],
            Ge = (e) => {
              (nt.delete(Qe.get(e)), Qe.set(e, null), yr.push(e));
            },
            sn = (e) => {
              let t = e.length;
              return [(t % 128) | 128, t >> 7, ...e];
            },
            fs = { i: 127, p: 127, j: 126, f: 125, d: 124, e: 111 },
            an = (e) => sn(Array.from(e, (t) => fs[t])),
            kt = (e, t) => {
              if (!nt) {
                nt = new WeakMap();
                var s = Qe.length;
                if (nt)
                  for (var o = 0; o < 0 + s; o++) {
                    var d = Qe.get(o);
                    d && nt.set(d, o);
                  }
              }
              if ((s = nt.get(e) || 0)) return s;
              s = yr.length ? yr.pop() : Qe.grow(1);
              try {
                Qe.set(s, e);
              } catch (E) {
                if (!(E instanceof TypeError)) throw E;
                ((t = Uint8Array.of(
                  0,
                  97,
                  115,
                  109,
                  1,
                  0,
                  0,
                  0,
                  1,
                  ...sn([
                    1,
                    96,
                    ...an(t.slice(1)),
                    ...an(t[0] === "v" ? "" : t[0]),
                  ]),
                  2,
                  7,
                  1,
                  1,
                  101,
                  1,
                  102,
                  0,
                  0,
                  7,
                  5,
                  1,
                  1,
                  102,
                  0,
                  0
                )),
                  (t = new WebAssembly.Module(t)),
                  (t = new WebAssembly.Instance(t, { e: { f: e } }).exports.f),
                  Qe.set(s, t));
              }
              return (nt.set(e, s), s);
            };
          if (
            ((Ze = Array(4096)),
            Wr(H, "/"),
            ze("/tmp"),
            ze("/home"),
            ze("/home/web_user"),
            (function () {
              (ze("/dev"),
                dr(259, {
                  read: () => 0,
                  write: (o, d, E, P) => P,
                  Ya: () => 0,
                }),
                Nt("/dev/null", 259),
                Nr(1280, es),
                Nr(1536, ts),
                Nt("/dev/tty", 1280),
                Nt("/dev/tty1", 1536));
              var e = new Uint8Array(1024),
                t = 0,
                s = () => (t === 0 && (Lr(e), (t = e.byteLength)), e[--t]);
              (Je("random", s),
                Je("urandom", s),
                ze("/dev/shm"),
                ze("/dev/shm/tmp"));
            })(),
            (function () {
              ze("/proc");
              var e = ze("/proc/self");
              (ze("/proc/self/fd"),
                Wr(
                  {
                    ab() {
                      var t = qr(e, "fd", 16895, 73);
                      return (
                        (t.Ma = { Ya: H.Ma.Ya }),
                        (t.La = {
                          mb(s, o) {
                            s = +o;
                            var d = ve(s);
                            return (
                              (s = {
                                parent: null,
                                ab: { Sb: "fake" },
                                La: { eb: () => d.path },
                                id: s + 1,
                              }),
                              (s.parent = s)
                            );
                          },
                          Ib() {
                            return Array.from(ut.entries())
                              .filter(([, s]) => s)
                              .map(([s]) => s.toString());
                          },
                        }),
                        t
                      );
                    },
                  },
                  "/proc/self/fd"
                ));
            })(),
            a.noExitRuntime && (Le = a.noExitRuntime),
            a.print && (g = a.print),
            a.printErr && (x = a.printErr),
            a.wasmBinary && (C = a.wasmBinary),
            a.thisProgram && (u = a.thisProgram),
            a.preInit)
          )
            for (
              typeof a.preInit == "function" && (a.preInit = [a.preInit]);
              0 < a.preInit.length;
            )
              a.preInit.shift()();
          ((a.stackSave = () => Ut()),
            (a.stackRestore = (e) => Kt(e)),
            (a.stackAlloc = (e) => st(e)),
            (a.cwrap = (e, t, s, o) => {
              var d = !s || s.every((E) => E === "number" || E === "boolean");
              return t !== "string" && d && !o
                ? a["_" + e]
                : (...E) => ds(e, t, s, E);
            }),
            (a.addFunction = kt),
            (a.removeFunction = Ge),
            (a.UTF8ToString = j),
            (a.stringToNewUTF8 = qt),
            (a.writeArrayToMemory = (e, t) => {
              F.set(e, t);
            }));
          var Ht,
            St,
            on,
            ln,
            Kt,
            st,
            Ut,
            Wt,
            Qe,
            hs = {
              a: (e, t, s, o) =>
                q(
                  `Assertion failed: ${j(e)}, at: ` +
                    [
                      t ? j(t) : "unknown filename",
                      s,
                      o ? j(o) : "unknown function",
                    ]
                ),
              i: function (e, t) {
                try {
                  return ((e = j(e)), jt(e, t), 0);
                } catch (s) {
                  if (typeof ne == "undefined" || s.name !== "ErrnoError")
                    throw s;
                  return -s.Pa;
                }
              },
              L: function (e, t, s) {
                try {
                  if (((t = j(t)), (t = rt(e, t)), s & -8)) return -28;
                  var o = Fe(t, { hb: !0 }).node;
                  return o
                    ? ((e = ""),
                      s & 4 && (e += "r"),
                      s & 2 && (e += "w"),
                      s & 1 && (e += "x"),
                      e && dt(o, e) ? -2 : 0)
                    : -44;
                } catch (d) {
                  if (typeof ne == "undefined" || d.name !== "ErrnoError")
                    throw d;
                  return -d.Pa;
                }
              },
              j: function (e, t) {
                try {
                  var s = ve(e);
                  return (Gr(s, s.node, t, !1), 0);
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return -o.Pa;
                }
              },
              h: function (e) {
                try {
                  var t = ve(e);
                  return (ur(t, t.node, { timestamp: Date.now(), dc: !1 }), 0);
                } catch (s) {
                  if (typeof ne == "undefined" || s.name !== "ErrnoError")
                    throw s;
                  return -s.Pa;
                }
              },
              b: function (e, t, s) {
                $t = s;
                try {
                  var o = ve(e);
                  switch (t) {
                    case 0:
                      var d = Vt();
                      if (0 > d) break;
                      for (; ut[d]; ) d++;
                      return as(o, d).bb;
                    case 1:
                    case 2:
                      return 0;
                    case 3:
                      return o.flags;
                    case 4:
                      return ((d = Vt()), (o.flags |= d), 0);
                    case 12:
                      return ((d = Vt()), (A[(d + 0) >> 1] = 2), 0);
                    case 13:
                    case 14:
                      return 0;
                  }
                  return -28;
                } catch (E) {
                  if (typeof ne == "undefined" || E.name !== "ErrnoError")
                    throw E;
                  return -E.Pa;
                }
              },
              g: function (e, t) {
                try {
                  var s = ve(e),
                    o = s.node,
                    d = s.Ma.Wa;
                  ((e = d ? s : o), d != null || (d = o.La.Wa), Lt(d));
                  var E = d(e);
                  return zt(t, E);
                } catch (P) {
                  if (typeof ne == "undefined" || P.name !== "ErrnoError")
                    throw P;
                  return -P.Pa;
                }
              },
              H: function (e, t) {
                t =
                  -9007199254740992 > t || 9007199254740992 < t
                    ? NaN
                    : Number(t);
                try {
                  if (isNaN(t)) return -61;
                  var s = ve(e);
                  if (0 > t || (s.flags & 2097155) === 0) throw new D(28);
                  return (Qr(s, s.node, t), 0);
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return -o.Pa;
                }
              },
              G: function (e, t) {
                try {
                  if (t === 0) return -28;
                  var s = pt("/") + 1;
                  return t < s ? -68 : (je("/", B, e, t), s);
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return -o.Pa;
                }
              },
              K: function (e, t) {
                try {
                  return ((e = j(e)), zt(t, xt(e, !0)));
                } catch (s) {
                  if (typeof ne == "undefined" || s.name !== "ErrnoError")
                    throw s;
                  return -s.Pa;
                }
              },
              C: function (e, t, s) {
                try {
                  return ((t = j(t)), (t = rt(e, t)), ze(t, s), 0);
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return -o.Pa;
                }
              },
              J: function (e, t, s, o) {
                try {
                  t = j(t);
                  var d = o & 256;
                  return (
                    (t = rt(e, t, o & 4096)),
                    zt(s, d ? xt(t, !0) : xt(t))
                  );
                } catch (E) {
                  if (typeof ne == "undefined" || E.name !== "ErrnoError")
                    throw E;
                  return -E.Pa;
                }
              },
              x: function (e, t, s, o) {
                $t = o;
                try {
                  ((t = j(t)), (t = rt(e, t)));
                  var d = o ? Vt() : 0;
                  return ft(t, s, d).bb;
                } catch (E) {
                  if (typeof ne == "undefined" || E.name !== "ErrnoError")
                    throw E;
                  return -E.Pa;
                }
              },
              v: function (e, t, s, o) {
                try {
                  if (((t = j(t)), (t = rt(e, t)), 0 >= o)) return -28;
                  var d = Fe(t).node;
                  if (!d) throw new D(44);
                  if (!d.La.eb) throw new D(28);
                  var E = d.La.eb(d),
                    P = Math.min(o, pt(E)),
                    $ = F[s + P];
                  return (je(E, B, s, o + 1), (F[s + P] = $), P);
                } catch (Q) {
                  if (typeof ne == "undefined" || Q.name !== "ErrnoError")
                    throw Q;
                  return -Q.Pa;
                }
              },
              u: function (e) {
                try {
                  return ((e = j(e)), Zr(e), 0);
                } catch (t) {
                  if (typeof ne == "undefined" || t.name !== "ErrnoError")
                    throw t;
                  return -t.Pa;
                }
              },
              f: function (e, t) {
                try {
                  return ((e = j(e)), zt(t, xt(e)));
                } catch (s) {
                  if (typeof ne == "undefined" || s.name !== "ErrnoError")
                    throw s;
                  return -s.Pa;
                }
              },
              r: function (e, t, s) {
                try {
                  if (((t = j(t)), (t = rt(e, t)), s))
                    if (s === 512) Zr(t);
                    else return -28;
                  else Jr(t);
                  return 0;
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return -o.Pa;
                }
              },
              q: function (e, t, s) {
                try {
                  ((t = j(t)), (t = rt(e, t, !0)));
                  var o = Date.now(),
                    d,
                    E;
                  if (s) {
                    var P = w[s >> 2] + 4294967296 * v[(s + 4) >> 2],
                      $ = v[(s + 8) >> 2];
                    ($ == 1073741823
                      ? (d = o)
                      : $ == 1073741822
                        ? (d = null)
                        : (d = 1e3 * P + $ / 1e6),
                      (s += 16),
                      (P = w[s >> 2] + 4294967296 * v[(s + 4) >> 2]),
                      ($ = v[(s + 8) >> 2]),
                      $ == 1073741823
                        ? (E = o)
                        : $ == 1073741822
                          ? (E = null)
                          : (E = 1e3 * P + $ / 1e6));
                  } else E = d = o;
                  if ((E != null ? E : d) !== null) {
                    e = d;
                    var Q = Fe(t, { hb: !0 }).node;
                    Lt(Q.La.Xa)(Q, { $a: e, Ua: E });
                  }
                  return 0;
                } catch (Z) {
                  if (typeof ne == "undefined" || Z.name !== "ErrnoError")
                    throw Z;
                  return -Z.Pa;
                }
              },
              m: () => q(""),
              l: () => {
                ((Le = !1), (gr = 0));
              },
              A: function (e, t) {
                ((e =
                  -9007199254740992 > e || 9007199254740992 < e
                    ? NaN
                    : Number(e)),
                  (e = new Date(1e3 * e)),
                  (v[t >> 2] = e.getSeconds()),
                  (v[(t + 4) >> 2] = e.getMinutes()),
                  (v[(t + 8) >> 2] = e.getHours()),
                  (v[(t + 12) >> 2] = e.getDate()),
                  (v[(t + 16) >> 2] = e.getMonth()),
                  (v[(t + 20) >> 2] = e.getFullYear() - 1900),
                  (v[(t + 24) >> 2] = e.getDay()));
                var s = e.getFullYear();
                ((v[(t + 28) >> 2] =
                  ((s % 4 !== 0 || (s % 100 === 0 && s % 400 !== 0) ? ps : cs)[
                    e.getMonth()
                  ] +
                    e.getDate() -
                    1) |
                  0),
                  (v[(t + 36) >> 2] = -(60 * e.getTimezoneOffset())),
                  (s = new Date(e.getFullYear(), 6, 1).getTimezoneOffset()));
                var o = new Date(e.getFullYear(), 0, 1).getTimezoneOffset();
                v[(t + 32) >> 2] =
                  (s != o && e.getTimezoneOffset() == Math.min(o, s)) | 0;
              },
              y: function (e, t, s, o, d, E, P) {
                d =
                  -9007199254740992 > d || 9007199254740992 < d
                    ? NaN
                    : Number(d);
                try {
                  var $ = ve(o);
                  if (
                    (t & 2) !== 0 &&
                    (s & 2) === 0 &&
                    ($.flags & 2097155) !== 2
                  )
                    throw new D(2);
                  if (($.flags & 2097155) === 1) throw new D(2);
                  if (!$.Ma.sb) throw new D(43);
                  if (!e) throw new D(28);
                  var Q = $.Ma.sb($, e, d, t, s),
                    Z = Q.tc;
                  return ((v[E >> 2] = Q.Ub), (w[P >> 2] = Z), 0);
                } catch (Y) {
                  if (typeof ne == "undefined" || Y.name !== "ErrnoError")
                    throw Y;
                  return -Y.Pa;
                }
              },
              z: function (e, t, s, o, d, E) {
                E =
                  -9007199254740992 > E || 9007199254740992 < E
                    ? NaN
                    : Number(E);
                try {
                  var P = ve(d);
                  if (s & 2) {
                    if ((P.node.mode & 61440) !== 32768) throw new D(43);
                    o & 2 ||
                      (P.Ma.tb && P.Ma.tb(P, B.slice(e, e + t), E, t, o));
                  }
                } catch ($) {
                  if (typeof ne == "undefined" || $.name !== "ErrnoError")
                    throw $;
                  return -$.Pa;
                }
              },
              n: (e, t) => {
                if ((wt[e] && (clearTimeout(wt[e].id), delete wt[e]), !t))
                  return 0;
                var s = setTimeout(() => {
                  (delete wt[e], us(() => ln(e, performance.now())));
                }, t);
                return ((wt[e] = { id: s, Hc: t }), 0);
              },
              B: (e, t, s, o) => {
                var d = new Date().getFullYear(),
                  E = new Date(d, 0, 1).getTimezoneOffset();
                ((d = new Date(d, 6, 1).getTimezoneOffset()),
                  (w[e >> 2] = 60 * Math.max(E, d)),
                  (v[t >> 2] = +(E != d)),
                  (t = (P) => {
                    var $ = Math.abs(P);
                    return `UTC${0 <= P ? "-" : "+"}${String(Math.floor($ / 60)).padStart(2, "0")}${String($ % 60).padStart(2, "0")}`;
                  }),
                  (e = t(E)),
                  (t = t(d)),
                  d < E
                    ? (je(e, B, s, 17), je(t, B, o, 17))
                    : (je(e, B, o, 17), je(t, B, s, 17)));
              },
              d: () => Date.now(),
              s: () => 2147483648,
              c: () => performance.now(),
              o: (e) => {
                var t = B.length;
                if (((e >>>= 0), 2147483648 < e)) return !1;
                for (var s = 1; 4 >= s; s *= 2) {
                  var o = t * (1 + 0.2 / s);
                  o = Math.min(o, e + 100663296);
                  e: {
                    o =
                      ((Math.min(
                        2147483648,
                        65536 * Math.ceil(Math.max(e, o) / 65536)
                      ) -
                        Wt.buffer.byteLength +
                        65535) /
                        65536) |
                      0;
                    try {
                      (Wt.grow(o), J());
                      var d = 1;
                      break e;
                    } catch (E) {}
                    d = void 0;
                  }
                  if (d) return !0;
                }
                return !1;
              },
              E: (e, t) => {
                var s = 0,
                  o = 0,
                  d;
                for (d of nn()) {
                  var E = t + s;
                  ((w[(e + o) >> 2] = E),
                    (s += je(d, B, E, 1 / 0) + 1),
                    (o += 4));
                }
                return 0;
              },
              F: (e, t) => {
                var s = nn();
                ((w[e >> 2] = s.length), (e = 0));
                for (var o of s) e += pt(o) + 1;
                return ((w[t >> 2] = e), 0);
              },
              e: function (e) {
                try {
                  var t = ve(e);
                  return (hr(t), 0);
                } catch (s) {
                  if (typeof ne == "undefined" || s.name !== "ErrnoError")
                    throw s;
                  return s.Pa;
                }
              },
              p: function (e, t) {
                try {
                  var s = ve(e);
                  return (
                    (F[t] = s.Va
                      ? 2
                      : Ee(s.mode)
                        ? 3
                        : (s.mode & 61440) === 40960
                          ? 7
                          : 4),
                    (A[(t + 2) >> 1] = 0),
                    (I[(t + 8) >> 3] = BigInt(0)),
                    (I[(t + 16) >> 3] = BigInt(0)),
                    0
                  );
                } catch (o) {
                  if (typeof ne == "undefined" || o.name !== "ErrnoError")
                    throw o;
                  return o.Pa;
                }
              },
              w: function (e, t, s, o) {
                try {
                  e: {
                    var d = ve(e);
                    e = t;
                    for (var E, P = (t = 0); P < s; P++) {
                      var $ = w[e >> 2],
                        Q = w[(e + 4) >> 2];
                      e += 8;
                      var Z = Yr(d, F, $, Q, E);
                      if (0 > Z) {
                        var Y = -1;
                        break e;
                      }
                      if (((t += Z), Z < Q)) break;
                      typeof E != "undefined" && (E += Z);
                    }
                    Y = t;
                  }
                  return ((w[o >> 2] = Y), 0);
                } catch (_e) {
                  if (typeof ne == "undefined" || _e.name !== "ErrnoError")
                    throw _e;
                  return _e.Pa;
                }
              },
              D: function (e, t, s, o) {
                t =
                  -9007199254740992 > t || 9007199254740992 < t
                    ? NaN
                    : Number(t);
                try {
                  if (isNaN(t)) return 61;
                  var d = ve(e);
                  return (
                    Xr(d, t, s),
                    (I[o >> 3] = BigInt(d.position)),
                    d.Eb && t === 0 && s === 0 && (d.Eb = null),
                    0
                  );
                } catch (E) {
                  if (typeof ne == "undefined" || E.name !== "ErrnoError")
                    throw E;
                  return E.Pa;
                }
              },
              I: function (e) {
                var s, o;
                try {
                  var t = ve(e);
                  return (o = (s = t.Ma) == null ? void 0 : s.lb) == null
                    ? void 0
                    : o.call(s, t);
                } catch (d) {
                  if (typeof ne == "undefined" || d.name !== "ErrnoError")
                    throw d;
                  return d.Pa;
                }
              },
              t: function (e, t, s, o) {
                try {
                  e: {
                    var d = ve(e);
                    e = t;
                    for (var E, P = (t = 0); P < s; P++) {
                      var $ = w[e >> 2],
                        Q = w[(e + 4) >> 2];
                      e += 8;
                      var Z = en(d, F, $, Q, E);
                      if (0 > Z) {
                        var Y = -1;
                        break e;
                      }
                      if (((t += Z), Z < Q)) break;
                      typeof E != "undefined" && (E += Z);
                    }
                    Y = t;
                  }
                  return ((w[o >> 2] = Y), 0);
                } catch (_e) {
                  if (typeof ne == "undefined" || _e.name !== "ErrnoError")
                    throw _e;
                  return _e.Pa;
                }
              },
              k: rn,
            };
          function br() {
            function e() {
              var d;
              if (((a.calledRun = !0), !R)) {
                if (!a.noFSInit && !$r) {
                  var t, s;
                  (($r = !0),
                    t != null || (t = a.stdin),
                    s != null || (s = a.stdout),
                    o != null || (o = a.stderr),
                    t ? Je("stdin", t) : fr("/dev/tty", "/dev/stdin"),
                    s ? Je("stdout", null, s) : fr("/dev/tty", "/dev/stdout"),
                    o ? Je("stderr", null, o) : fr("/dev/tty1", "/dev/stderr"),
                    ft("/dev/stdin", 0),
                    ft("/dev/stdout", 1),
                    ft("/dev/stderr", 1));
                }
                if (
                  (vr.N(),
                  (Vr = !1),
                  (d = a.onRuntimeInitialized) == null || d.call(a),
                  a.postRun)
                )
                  for (
                    typeof a.postRun == "function" && (a.postRun = [a.postRun]);
                    a.postRun.length;
                  ) {
                    var o = a.postRun.shift();
                    U.push(o);
                  }
                V(U);
              }
            }
            if (0 < ge) Ce = br;
            else {
              if (a.preRun)
                for (
                  typeof a.preRun == "function" && (a.preRun = [a.preRun]);
                  a.preRun.length;
                )
                  we();
              (V(be),
                0 < ge
                  ? (Ce = br)
                  : a.setStatus
                    ? (a.setStatus("Running..."),
                      setTimeout(() => {
                        (setTimeout(() => a.setStatus(""), 1), e());
                      }, 1))
                    : e());
            }
          }
          var vr;
          return (
            (async function () {
              var s;
              function e(o) {
                var d;
                return (
                  (o = vr = o.exports),
                  (a._sqlite3_free = o.P),
                  (a._sqlite3_value_text = o.Q),
                  (a._sqlite3_prepare_v2 = o.R),
                  (a._sqlite3_step = o.S),
                  (a._sqlite3_reset = o.T),
                  (a._sqlite3_exec = o.U),
                  (a._sqlite3_finalize = o.V),
                  (a._sqlite3_column_name = o.W),
                  (a._sqlite3_column_text = o.X),
                  (a._sqlite3_column_type = o.Y),
                  (a._sqlite3_errmsg = o.Z),
                  (a._sqlite3_clear_bindings = o._),
                  (a._sqlite3_value_blob = o.$),
                  (a._sqlite3_value_bytes = o.aa),
                  (a._sqlite3_value_double = o.ba),
                  (a._sqlite3_value_int = o.ca),
                  (a._sqlite3_value_type = o.da),
                  (a._sqlite3_result_blob = o.ea),
                  (a._sqlite3_result_double = o.fa),
                  (a._sqlite3_result_error = o.ga),
                  (a._sqlite3_result_int = o.ha),
                  (a._sqlite3_result_int64 = o.ia),
                  (a._sqlite3_result_null = o.ja),
                  (a._sqlite3_result_text = o.ka),
                  (a._sqlite3_aggregate_context = o.la),
                  (a._sqlite3_column_count = o.ma),
                  (a._sqlite3_data_count = o.na),
                  (a._sqlite3_column_blob = o.oa),
                  (a._sqlite3_column_bytes = o.pa),
                  (a._sqlite3_column_double = o.qa),
                  (a._sqlite3_bind_blob = o.ra),
                  (a._sqlite3_bind_double = o.sa),
                  (a._sqlite3_bind_int = o.ta),
                  (a._sqlite3_bind_text = o.ua),
                  (a._sqlite3_bind_parameter_index = o.va),
                  (a._sqlite3_sql = o.wa),
                  (a._sqlite3_normalized_sql = o.xa),
                  (a._sqlite3_changes = o.ya),
                  (a._sqlite3_close_v2 = o.za),
                  (a._sqlite3_create_function_v2 = o.Aa),
                  (a._sqlite3_update_hook = o.Ba),
                  (a._sqlite3_open = o.Ca),
                  (Ht = a._malloc = o.Da),
                  (St = a._free = o.Ea),
                  (a._RegisterExtensionFunctions = o.Fa),
                  (on = o.Ga),
                  (ln = o.Ha),
                  (Kt = o.Ia),
                  (st = o.Ja),
                  (Ut = o.Ka),
                  (Wt = o.M),
                  (Qe = o.O),
                  J(),
                  ge--,
                  (d = a.monitorRunDependencies) == null || d.call(a, ge),
                  ge == 0 && Ce && ((o = Ce), (Ce = null), o()),
                  vr
                );
              }
              (ge++, (s = a.monitorRunDependencies) == null || s.call(a, ge));
              var t = { a: hs };
              return a.instantiateWasm
                ? new Promise((o) => {
                    a.instantiateWasm(t, (d, E) => {
                      o(e(d, E));
                    });
                  })
                : (te != null ||
                    (te = a.locateFile
                      ? a.locateFile("sql-wasm-browser.wasm", h)
                      : h + "sql-wasm-browser.wasm"),
                  e((await ye(t)).instance));
            })(),
            br(),
            n
          );
        })),
        tr)
      );
    };
  typeof nr == "object" && typeof Ot == "object"
    ? ((Ot.exports = rr), (Ot.exports.default = rr))
    : typeof define == "function" && define.amd
      ? define([], function () {
          return rr;
        })
      : typeof nr == "object" && (nr.Module = rr);
});
var na = {};
Ws(na, { default: () => ar });
module.exports = Zs(na);
var de = require("obsidian"),
  le = ae(require("fs")),
  bt = ae(require("path")),
  He = require("child_process");
var it = "paperforge-status",
  Ct = "paperforge",
  xn =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  Pe = [
    {
      id: "paperforge-sync",
      title: "Sync Library",
      desc: "Pull new references from Zotero and generate literature notes",
      icon: "\u21BB",
      cmd: "sync",
      okMsg: "Sync complete",
    },
    {
      id: "paperforge-ocr",
      title: "Run OCR",
      desc: "Extract full text and figures from PDFs via PaddleOCR",
      icon: "\u229E",
      cmd: "ocr",
      okMsg: "OCR started",
    },
    {
      id: "paperforge-doctor",
      title: "Run Doctor",
      desc: "Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health",
      icon: "\u2695",
      cmd: "doctor",
      okMsg: "Doctor complete",
    },
    {
      id: "paperforge-repair",
      title: "Repair Issues",
      desc: "Fix three-way state divergence, path errors, and rebuild index",
      icon: "\u21BA",
      cmd: "repair",
      args: ["--fix", "--fix-paths"],
      okMsg: "Repair complete",
    },
    {
      id: "paperforge-ocr-redo",
      title: "Redo OCR",
      desc: "Re-run OCR for papers marked ocr_redo: true",
      icon: "\u21BA",
      cmd: "ocr",
      args: ["redo"],
      okMsg: "OCR redo started",
    },
  ],
  Ft = {
    vault_path: "",
    setup_complete: !1,
    auto_update: !0,
    auto_update_on_startup: !0,
    agent_platform: "opencode",
    language: "",
    paddleocr_api_key: "",
    zotero_data_dir: "",
    python_path: "",
    features: { memory_layer: !0, vector_db: !1 },
    selected_skill_platform: "opencode",
    vector_db_api_key: "",
    vector_db_api_base: "",
    vector_db_api_model: "text-embedding-3-small",
    frozen_skills: {},
    system_dir: "",
    resources_dir: "",
    literature_dir: "",
    base_dir: "",
    last_seen_version: "",
  };
function wn(_, y) {
  if (!y || !y.note_path) return y;
  let r = _.vault.getAbstractFileByPath(y.note_path);
  if (!r) return y;
  let n = _.metadataCache.getFileCache(r),
    i = n && n.frontmatter;
  if (!i) return y;
  let a = { ...y };
  for (let c of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(i, c) && (a[c] = i[c]);
  return a;
}
function xr(_, y) {
  return _ && { ..._, ...y };
}
var wr = {
    en: {
      action_running: "Running ",
      api_key_missing: "Missing",
      api_key_set: "Entered",
      btn_install: "Open Setup Wizard",
      btn_install_desc:
        "Check whether the environment is ready, then open the step-by-step setup wizard",
      btn_reconfig: "Reconfigure",
      btn_reconfig_desc:
        "Open the setup wizard again to change directories, platform, or API keys",
      btn_validate: "Validate",
      check_bbt_fail: "Not detected",
      check_bbt_ok: "Installed",
      check_python_fail: "Not found",
      check_python_ok: "Ready",
      check_zotero_fail: "Not detected",
      check_zotero_ok: "Found",
      complete_export_path: "Save Better BibTeX JSON exports into:",
      complete_next: "Recommended next steps",
      complete_step1: "Open Dashboard",
      complete_step1_desc:
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
      complete_step2: "Sync Literature",
      complete_step2_desc:
        "In the main panel, click Sync Library to bring papers from Zotero into Obsidian and generate notes.",
      complete_step3: "Run OCR",
      complete_step3_desc:
        "In the Obsidian Base view, mark do_ocr:true on papers, then run OCR in the main panel.",
      complete_step4: "Configure Better BibTeX Auto-export",
      complete_step4_desc:
        'In Zotero, right-click the library or collection you want to sync -> Export -> Better BibTeX JSON -> enable "Keep updated".',
      complete_summary: "Saved Configuration",
      complete_title: "Setup Complete",
      copied: "Copied!",
      copy_pf_deep_cmd: "Copy /pf-deep Command",
      dashboard_drift_warning:
        "PaperForge CLI (v{0}) differs from plugin (v{1}). Open Settings \u2192 Runtime Health to sync.",
      deep_reading_not_found: "Deep reading file not found",
      desc: "Obsidian + Zotero literature pipeline. Sync papers, generate notes, run OCR, and read deeply in one place.",
      dir_base: "Base Dir",
      dir_index: "Index Dir",
      dir_notes: "Notes Dir",
      dir_resources: "Resource Dir",
      dir_system: "System Dir",
      dir_vault: "Vault Path",
      error_copied: "Copied!",
      error_copy_diagnostic: "Copy diagnostic",
      feat_agent_platform: "Agent Platform",
      feat_agent_platform_desc:
        "Select which agent platform to manage skills for.",
      feat_api_base_url: "API Base URL",
      feat_api_base_url_desc:
        "Custom OpenAI-compatible API endpoint. Leave empty for default.",
      feat_api_model: "API Model",
      feat_api_model_desc: "Embedding model name for this endpoint.",
      feat_build_btn: "Build",
      feat_build_complete: "Vector build complete.",
      feat_build_failed: "Build failed. See terminal output.",
      feat_building: "Building...",
      feat_cache_remove_failed: "Failed: {0}",
      feat_cache_removed: "Model cache removed.",
      feat_checking: "Checking...",
      feat_checking_btn: "Checking...",
      feat_deps_checking: "Checking dependencies...",
      feat_deps_missing:
        "Dependencies not installed. Required: chromadb, openai.",
      feat_enter_key: "Enter a valid OpenAI API key.",
      feat_install_btn: "Install",
      feat_install_deps: "Install Dependencies",
      feat_install_deps_desc: "pip install chromadb openai (~35MB).",
      feat_install_done: "Dependencies installed. Building vectors...",
      feat_install_failed: "Install failed: ",
      feat_installing: "Installing...",
      feat_installing_pkgs: "Installing {pkgs}...",
      feat_key_rejected: "API key rejected.",
      feat_memory_desc:
        "The Memory Layer is the core data engine of PaperForge, powered by SQLite. It integrates literature metadata (papers, assets, aliases, reading events), provides FTS5 metadata search across titles, abstracts, authors, domains, and collections, and powers agent-context and paper-status. Always active \u2014 no toggle needed.",
      feat_memory_rebuild_btn: "Rebuild",
      feat_memory_rebuild_done: "Memory DB rebuilt.",
      feat_memory_rebuild_failed: "Rebuild failed.",
      feat_memory_rebuilding: "Rebuilding...",
      feat_model_changed_warn:
        "Model changed ({0} -> {1}). Existing vectors are incompatible \u2014 rebuild required.",
      feat_network_error: "Network error: ",
      feat_no_python: "No Python found. Check Installation tab.",
      feat_not_cached: "Not cached",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "Used for API embedding calls. Model is defined below.",
      feat_output_copied: "Output copied to clipboard.",
      feat_rebuild_btn: "Rebuild",
      feat_rebuild_vectors: "Rebuild Vectors",
      feat_rebuild_vectors_changed:
        "Model changed \u2014 rebuild to update all vectors.",
      feat_rebuild_vectors_desc:
        "Rebuild all OCR fulltext vectors. Required after model or mode change.",
      feat_removing: "Removing...",
      feat_retry_btn: "Retry",
      feat_skills_desc:
        "Manage and enable/disable agent skills installed in your vault. Each row corresponds to a SKILL.md file \u2014 toggle off to prevent the agent from auto-invoking that skill.",
      feat_skills_system:
        "System Skills ship with PaperForge and are updated alongside PaperForge.",
      feat_skills_user:
        "User Skills are custom skills you install from community or create yourself.",
      feat_uninstall_btn: "Uninstall",
      feat_valid_key: "API key valid.",
      feat_vector_config_label: "Vector Settings",
      feat_vector_corrupted:
        "Vector index corrupted \u2014 needs force rebuild.",
      feat_vector_desc:
        "Vector Database enables semantic search across OCR-extracted fulltext via API embedding. Documents are split into chunks, embedded via OpenAI-compatible API, and stored in ChromaDB.",
      feat_vector_enable: "Enable Vector Retrieval",
      feat_vector_enable_desc:
        "Semantic search across OCR fulltext. Requires: pip install openai chromadb (~35MB).",
      feat_vector_rebuild_force_btn: "Force Rebuild",
      feat_verify: "Verify",
      feat_verify_btn: "Verify",
      field_paddleocr: "PaddleOCR API Key",
      field_python_custom: "Custom Path",
      field_python_interp: "Python Interpreter",
      field_zotero_data: "Zotero Data Dir",
      field_zotero_placeholder:
        "Required. Path to Zotero data directory for PDF attachment resolution.",
      guide_ocr: "Run OCR",
      guide_ocr_desc:
        "In the main panel, click Run OCR to extract full text and figures from PDFs for later reading and analysis.",
      guide_open: "Open Main Panel",
      guide_open_desc:
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
      guide_sync: "Sync Literature",
      guide_sync_desc:
        "After Better BibTeX JSON export is configured, click Sync Library to import papers from Zotero into Obsidian and generate notes automatically.",
      header_title: "PaperForge",
      install_bootstrapping:
        "PaperForge Python package not found. Installing automatically...",
      install_btn: "Start Install",
      install_btn_retry: "Retry",
      install_btn_running: "Installing...",
      install_complete: "Installation complete!",
      install_failed: "Installation failed: ",
      install_validating: "Validating setup...",
      jump_to_deep_reading: "Open Deep Reading",
      label_agent: "Agent Platform",
      nav_close: "Close",
      nav_next: "Next",
      nav_prev: "Back",
      not_set: "Not entered",
      notice_check_fail: "Missing: ",
      notice_python_missing:
        "Python was not detected. Install Python 3.10+ and add it to PATH.",
      ocr_privacy_title: "OCR Privacy Notice",
      ocr_privacy_warning:
        "OCR will upload PDFs to the PaddleOCR API. Do not upload sensitive or confidential documents.",
      ocr_queue_add: "Add to OCR Queue",
      ocr_queue_added: "Added to OCR queue",
      ocr_queue_remove: "Remove from OCR Queue",
      ocr_queue_removed: "Removed from OCR queue",
      ocr_understand: "I understand, continue",
      optional_later: "(can be set later in Settings)",
      orphan_delete_failed: "Prune failed",
      orphan_delete_selected: "Delete {count} selected",
      orphan_deleted: "Deleted {count} orphan workspace(s)",
      orphan_desc: "These papers are no longer in your Zotero library.",
      orphan_deselect_all: "Deselect all",
      orphan_explain: "Removed from Zotero. Workspace files remain on disk.",
      orphan_keep_all: "Keep all",
      orphan_none_selected: "No papers selected for deletion",
      orphan_select_all: "Select all",
      orphan_title: "Found {count} orphan paper(s)",
      panel_actions: "Quick Actions",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc: "In Zotero: Tools -> Add-ons -> install Better BibTeX.",
      prep_export: "Better BibTeX Auto-export",
      prep_export_desc:
        'In Zotero, right-click the collection you want to sync -> Export Collection -> BetterBibTeX JSON -> enable "Keep updated" -> save the JSON file into the exports folder shown below. Obsidian Base views will use the JSON filename as the Base name:',
      prep_export_path_label: "Save the exported JSON file into this folder:",
      prep_key: "PaddleOCR Key",
      prep_key_desc:
        "Get your API key from https://aistudio.baidu.com/paddleocr",
      prep_python: "Python 3.10+",
      prep_python_desc:
        "Python must be available from the command line. If you are not sure, click below to auto-detect.",
      prep_zotero: "Zotero Desktop",
      prep_zotero_desc: "Install Zotero from https://www.zotero.org",
      run_in_agent: "Run in {0}",
      runtime_health: "Runtime Health",
      runtime_health_checking: "Checking...",
      runtime_health_desc:
        "Check whether the installed paperforge Python package matches the plugin version and whether the deployed skill contract is current.",
      runtime_health_match: "Match",
      runtime_health_mismatch: "Mismatch",
      runtime_health_package_ver: "Python package v{0}",
      runtime_health_plugin_ver: "Plugin v{0}",
      runtime_health_sync: "Sync Runtime",
      runtime_health_sync_done: "Runtime synced to v{0}",
      runtime_health_sync_fail: "Sync failed: {0}",
      runtime_health_syncing: "Syncing...",
      section_config: "Current Configuration",
      section_guide: "How To Use",
      section_prep: "Preparation",
      section_prep_desc:
        "Before first use, finish these 4 preparation items. Better BibTeX auto-export is configured after setup:",
      setup_done: "PaperForge environment is ready",
      setup_pending:
        "Not installed yet. Finish the preparation items below, then open the wizard.",
      tab_features: "Features",
      tab_setup: "Installation",
      tab_maintenance: "Maintenance",
      validate_base: "Base directory is required",
      validate_fail: "Please complete the required fields below",
      validate_index: "Index directory is required",
      validate_key: "PaddleOCR API key (optional, needed for OCR)",
      validate_notes: "Notes directory is required",
      validate_resources: "Resources directory is required",
      validate_system: "System directory is required",
      validate_vault: "Vault path is required",
      validate_zotero:
        "Zotero data directory (optional, needed for PDF linking)",
      wizard_agent_hint:
        "Choose the AI agent platform you use most often. PaperForge will place the matching command and skill files in the correct location.",
      wizard_dir_hint:
        "PaperForge stores user-facing literature data under the resources directory. These folders will live there:",
      wizard_dir_sub_hint: "Resolved folder preview based on the names below:",
      wizard_intro:
        "This wizard walks you through the full setup. In most cases, the default values are fine to keep.",
      wizard_keys_hint:
        "Enter your PaddleOCR API key below. If you want PaperForge to auto-locate Zotero PDFs, you can also fill in the Zotero data directory.",
      wizard_preview:
        "After installation, system files stay at the vault root while literature data stays under the resources directory.",
      wizard_safety:
        "Safety: if the selected folders already contain files, setup preserves existing files and only creates missing PaperForge folders and files.",
      wizard_step1: "Overview",
      wizard_step2: "Directory Setup",
      wizard_step3: "Platform & Keys",
      wizard_step4: "Install",
      wizard_step5: "Done",
      wizard_skip_ocr_desc:
        "OCR will not be available until you configure a valid PaddleOCR API key. You can continue setup now and configure it later in Settings.",
      wizard_skip_ocr_continue: "Continue without OCR key",
      wizard_skip_ocr_back: "Back to configure",
      wizard_api_hint_skip:
        "OCR key is optional \u2014 you may skip it and configure later.",
      wizard_sys_hint:
        "These folders live at the vault root, outside the resources directory:",
      wizard_title: "PaperForge Setup Wizard",
      ocr_maint_no_action: "No Action Needed",
      ocr_maint_rebuild: "Rebuild Recommended",
      ocr_maint_failed: "OCR Failed",
      ocr_maint_limited: "Result Limited",
      ocr_maint_needs_attention: "Needs Attention",
      ocr_maint_limitations: "Result Limitations",
      ocr_maint_hero_ok: "OCR looks usable overall.",
      ocr_maint_hero_warn:
        "OCR needs attention: {rebuild} rebuild recommended, {failed} failed.",
      ocr_maint_hero_note:
        "This page only promotes issues where maintenance is likely to help. Some papers may have limitations that maintenance will not improve.",
      ocr_maint_limitations_intro:
        "These papers look less certain, but PaperForge does not currently have a high-confidence maintenance action to recommend.",
      ocr_maint_all_papers: "All Papers",
      ocr_maint_rebuild_btn: "Rebuild results",
      ocr_maint_redo_btn: "Rerun OCR",
      maintenance_group_retry: "Needs Retry",
      maintenance_group_rebuild: "Can Rebuild",
      maintenance_group_legacy: "Upgrade Available (Optional)",
      maintenance_btn_retry: "Retry",
      maintenance_btn_rebuild: "Rebuild",
      maintenance_btn_upgrade: "Upgrade",
      maintenance_refresh_spinning: "Updating\u2026",
      maintenance_all_good: "\u2705 All good \u2014 no action needed",
      maintenance_n_pending: "{n} need attention",
      version_panel_title: "Version History",
      version_panel_back: "Back",
      version_filter_placeholder: "Filter papers...",
      version_papers_count: "{n} papers",
      version_current: "current",
      version_restore_btn: "Restore",
      version_compare_btn: "Compare",
      version_restore_selected: "Restore selected",
      version_clear_old: "Clear old versions (free {size})",
      version_no_backups: "No version history available",
      version_restore_confirm: "Restore {label} for {paper}?",
      version_restore_done: "Restored {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} paragraphs changed",
      version_error_read: "Cannot read version data",
    },
    zh: {
      action_running: "\u6B63\u5728\u6267\u884C ",
      api_key_missing: "\u672A\u914D\u7F6E \u2717",
      api_key_set: "\u5DF2\u914D\u7F6E \u2713",
      btn_install: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      btn_install_desc:
        "\u81EA\u52A8\u68C0\u6D4B Python + \u524D\u7F6E\u73AF\u5883\uFF0C\u901A\u8FC7\u540E\u6253\u5F00\u5206\u6B65\u5B89\u88C5\u5411\u5BFC",
      btn_reconfig: "\u91CD\u65B0\u914D\u7F6E",
      btn_reconfig_desc:
        "\u91CD\u65B0\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\uFF0C\u4FEE\u6539\u76EE\u5F55\u6216\u5BC6\u94A5\u914D\u7F6E",
      btn_validate: "\u9A8C\u8BC1",
      check_bbt_fail: "\u672A\u68C0\u6D4B\u5230",
      check_bbt_ok: "\u5DF2\u5B89\u88C5",
      check_python_fail: "\u672A\u5B89\u88C5",
      check_python_ok: "\u5DF2\u5C31\u7EEA",
      check_zotero_fail: "\u672A\u68C0\u6D4B\u5230",
      check_zotero_ok: "\u5DF2\u5B89\u88C5",
      complete_next: "\u4E0B\u4E00\u6B65\u64CD\u4F5C",
      complete_step1: "\u6253\u5F00 PaperForge Dashboard",
      complete_step1_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      complete_step2: "\u540C\u6B65\u6587\u732E",
      complete_step2_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      complete_step3: "\u8FD0\u884C OCR",
      complete_step3_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      complete_step4: "\u914D\u7F6E BBT \u81EA\u52A8\u5BFC\u51FA",
      complete_summary: "\u5F53\u524D\u5B8C\u6574\u914D\u7F6E",
      complete_title: "\u2713 PaperForge \u5B89\u88C5\u5B8C\u6210",
      copied: "\u5DF2\u590D\u5236\uFF01",
      copy_pf_deep_cmd: "\u590D\u5236 /pf-deep \u547D\u4EE4",
      dashboard_drift_warning:
        '\u63D2\u4EF6\u7248\u672C\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u4E0D\u5339\u914D\u3002\u8BF7\u5728\u8BBE\u7F6E\u4E2D\u70B9\u51FB"\u540C\u6B65\u8FD0\u884C\u65F6"\u3002',
      deep_reading_not_found: "\u7CBE\u8BFB\u6587\u4EF6\u672A\u627E\u5230",
      desc: "Obsidian + Zotero \u6587\u732E\u7BA1\u7406\u6D41\u6C34\u7EBF\u3002\u81EA\u52A8\u540C\u6B65\u6587\u732E\u3001\u751F\u6210\u7B14\u8BB0\u3001OCR \u63D0\u53D6\u5168\u6587\uFF0C\u4E00\u7AD9\u5F0F\u6587\u732E\u7CBE\u8BFB\u5DE5\u4F5C\u6D41\u3002",
      dir_base: "Base \u76EE\u5F55",
      dir_index: "\u7D22\u5F15\u76EE\u5F55",
      dir_notes: "\u6B63\u6587\u76EE\u5F55",
      dir_resources: "\u8D44\u6E90\u76EE\u5F55",
      dir_system: "\u7CFB\u7EDF\u76EE\u5F55",
      dir_vault: "Vault \u8DEF\u5F84",
      error_copied: "\u5DF2\u590D\u5236\uFF01",
      error_copy_diagnostic: "\u590D\u5236\u8BCA\u65AD\u4FE1\u606F",
      feat_agent_platform: "Agent \u5E73\u53F0",
      feat_agent_platform_desc:
        "\u9009\u62E9\u8981\u7BA1\u7406\u7684 Agent \u5E73\u53F0\u3002",
      feat_api_base_url: "API \u5730\u5740",
      feat_api_base_url_desc:
        "\u81EA\u5B9A\u4E49 OpenAI \u517C\u5BB9 API \u7AEF\u70B9\u3002\u7559\u7A7A\u4F7F\u7528\u9ED8\u8BA4\u5730\u5740\u3002",
      feat_api_model: "API \u6A21\u578B",
      feat_api_model_desc:
        "\u8BE5\u7AEF\u70B9\u4F7F\u7528\u7684\u5D4C\u5165\u6A21\u578B\u540D\u79F0\u3002",
      feat_build_btn: "\u6784\u5EFA",
      feat_build_complete: "\u5411\u91CF\u6784\u5EFA\u5B8C\u6210\u3002",
      feat_build_failed:
        "\u6784\u5EFA\u5931\u8D25\u3002\u8BF7\u67E5\u770B\u7EC8\u7AEF\u8F93\u51FA\u3002",
      feat_building: "\u6784\u5EFA\u4E2D\u2026",
      feat_cache_remove_failed: "\u5931\u8D25\uFF1A{0}",
      feat_cache_removed: "\u6A21\u578B\u7F13\u5B58\u5DF2\u6E05\u9664\u3002",
      feat_checking: "\u68C0\u6D4B\u4E2D\u2026",
      feat_checking_btn: "\u68C0\u6D4B\u4E2D\u2026",
      feat_deps_checking: "\u6B63\u5728\u68C0\u6D4B\u4F9D\u8D56\u2026",
      feat_deps_missing:
        "\u4F9D\u8D56\u672A\u5B89\u88C5\u3002\u9700\u8981\uFF1Achromadb, openai\u3002",
      feat_enter_key:
        "\u8BF7\u8F93\u5165\u6709\u6548\u7684 OpenAI API Key\u3002",
      feat_install_btn: "\u5B89\u88C5",
      feat_install_deps: "\u5B89\u88C5\u4F9D\u8D56",
      feat_install_done:
        "\u4F9D\u8D56\u5DF2\u5B89\u88C5\u3002\u6B63\u5728\u6784\u5EFA\u5411\u91CF\u2026",
      feat_install_failed: "\u5B89\u88C5\u5931\u8D25\uFF1A",
      feat_installing: "\u5B89\u88C5\u4E2D\u2026",
      feat_installing_pkgs: "\u6B63\u5728\u5B89\u88C5 {pkgs}...",
      feat_key_rejected: "API Key \u88AB\u62D2\u7EDD\u3002",
      feat_memory_desc:
        "\u8BB0\u5FC6\u5C42\u662F PaperForge \u7684\u6838\u5FC3\u6570\u636E\u5F15\u64CE\uFF0C\u57FA\u4E8E SQLite \u6784\u5EFA\u3002\u5B83\u6574\u5408\u4E86\u6587\u732E\u5143\u6570\u636E\uFF08\u8BBA\u6587\u3001\u8D44\u6E90\u6587\u4EF6\u3001\u522B\u540D\u3001\u9605\u8BFB\u4E8B\u4EF6\uFF09\uFF0C\u652F\u6301 FTS5 \u5143\u6570\u636E\u68C0\u7D22\uFF08\u6807\u9898\u3001\u6458\u8981\u3001\u4F5C\u8005\u3001domain\u3001collection\uFF09\uFF0C\u5E76\u4E3A agent-context \u548C paper-status \u547D\u4EE4\u63D0\u4F9B\u6570\u636E\u652F\u6491\u3002\u59CB\u7EC8\u8FD0\u884C\uFF0C\u65E0\u9700\u624B\u52A8\u5F00\u542F\u3002",
      feat_memory_rebuild_btn: "\u91CD\u5EFA\u6570\u636E\u5E93",
      feat_memory_rebuild_done:
        "\u8BB0\u5FC6\u6570\u636E\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002",
      feat_memory_rebuild_failed: "\u91CD\u5EFA\u5931\u8D25\u3002",
      feat_memory_rebuilding: "\u91CD\u5EFA\u4E2D\u2026",
      feat_model: "\u6A21\u578B",
      feat_model_changed_warn:
        "\u6A21\u578B\u5DF2\u66F4\u6362\uFF08{0} -> {1}\uFF09\u3002\u5DF2\u6709\u5411\u91CF\u4E0D\u517C\u5BB9\u2014\u2014\u9700\u8981\u91CD\u5EFA\u3002",
      feat_network_error: "\u7F51\u7EDC\u9519\u8BEF\uFF1A",
      feat_no_python:
        "\u672A\u627E\u5230 Python\u3002\u8BF7\u67E5\u770B\u5B89\u88C5\u6807\u7B7E\u9875\u3002",
      feat_not_cached: "\u672A\u7F13\u5B58",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "\u7528\u4E8E API \u5D4C\u5165\u8C03\u7528\uFF0C\u6A21\u578B\u5728\u4E0B\u65B9\u5B9A\u4E49\u3002",
      feat_output_copied:
        "\u8F93\u51FA\u5DF2\u590D\u5236\u5230\u526A\u8D34\u677F\u3002",
      feat_rebuild_btn: "\u91CD\u5EFA",
      feat_rebuild_vectors: "\u91CD\u5EFA\u5411\u91CF",
      feat_rebuild_vectors_changed:
        "\u6A21\u578B\u5DF2\u66F4\u6362 \u2014 \u9700\u8981\u91CD\u5EFA\u5411\u91CF\u3002",
      feat_rebuild_vectors_desc:
        "\u91CD\u5EFA\u6240\u6709 OCR \u5168\u6587\u5411\u91CF\u3002\u66F4\u6362\u6A21\u578B\u6216\u6A21\u5F0F\u540E\u9700\u8981\u91CD\u5EFA\u3002",
      feat_removing: "\u5220\u9664\u4E2D\u2026",
      feat_retry_btn: "\u91CD\u8BD5",
      feat_skills_desc:
        "\u7BA1\u7406 Vault \u4E2D\u5DF2\u5B89\u88C5\u7684 Agent \u6280\u80FD\u3002\u6BCF\u884C\u5BF9\u5E94\u4E00\u4E2A SKILL.md \u6587\u4EF6\uFF0C\u5173\u95ED\u5F00\u5173\u53EF\u963B\u6B62 Agent \u81EA\u52A8\u8C03\u7528\u8BE5\u6280\u80FD\u3002",
      feat_skills_system:
        "\u7CFB\u7EDF\u6280\u80FD\u968F PaperForge \u4E00\u540C\u53D1\u5E03\uFF0C\u4F1A\u8DDF\u968F PaperForge \u7248\u672C\u66F4\u65B0\u3002",
      feat_skills_user:
        "\u7528\u6237\u6280\u80FD\u662F\u4F60\u81EA\u884C\u5B89\u88C5\u6216\u521B\u5EFA\u7684\u81EA\u5B9A\u4E49\u6280\u80FD\u3002",
      feat_uninstall_btn: "\u5378\u8F7D",
      feat_valid_key: "API Key \u6709\u6548\u3002",
      feat_vector_config_label: "\u5411\u91CF\u5E93\u914D\u7F6E",
      feat_vector_corrupted:
        "\u5411\u91CF\u7D22\u5F15\u5DF2\u635F\u574F \u2014 \u9700\u8981\u5F3A\u5236\u91CD\u5EFA\u3002",
      feat_vector_desc:
        "\u5411\u91CF\u6570\u636E\u5E93\u901A\u8FC7\u5D4C\u5165\u6A21\u578B\u5B9E\u73B0 OCR \u5168\u6587\u7684\u8BED\u4E49\u641C\u7D22\u3002\u6587\u6863\u88AB\u5207\u5206\u4E3A\u6587\u672C\u5757\uFF08chunk\uFF09\uFF0C\u7F16\u7801\u4E3A\u5411\u91CF\u5B58\u5165 ChromaDB\u3002\u652F\u6301\u672C\u5730\u6A21\u578B\uFF08\u514D\u8D39\uFF0CCPU \u8FD0\u884C\uFF09\u6216 OpenAI API\uFF08\u4ED8\u8D39\uFF0C\u66F4\u5FEB\u901F\uFF09\u3002",
      feat_vector_enable: "\u542F\u7528\u5411\u91CF\u68C0\u7D22",
      feat_vector_enable_desc:
        "\u5BF9 OCR \u5168\u6587\u8FDB\u884C\u8BED\u4E49\u641C\u7D22\u3002\u9700\u5B89\u88C5: pip install chromadb sentence-transformers openai (~500MB)\u3002",
      feat_vector_rebuild_force_btn: "\u5F3A\u5236\u91CD\u5EFA",
      feat_verify: "\u9A8C\u8BC1",
      feat_verify_btn: "\u9A8C\u8BC1",
      field_paddleocr: "PaddleOCR API \u5BC6\u94A5",
      field_python_custom: "\u81EA\u5B9A\u4E49 Python \u8DEF\u5F84",
      field_python_interp: "\u5F53\u524D Python \u89E3\u91CA\u5668",
      field_zotero_data: "Zotero \u6570\u636E\u76EE\u5F55",
      field_zotero_placeholder:
        "\u53EF\u9009\uFF0C\u7528\u4E8E\u81EA\u52A8\u68C0\u6D4B PDF",
      guide_ocr: "\u8FD0\u884C OCR",
      guide_ocr_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      guide_open: "\u6253\u5F00 Dashboard",
      guide_open_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      guide_sync: "\u540C\u6B65\u6587\u732E",
      guide_sync_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      header_title: "PaperForge",
      install_bootstrapping:
        "\u672A\u68C0\u6D4B\u5230 PaperForge Python \u5305\uFF0C\u6B63\u5728\u81EA\u52A8\u5B89\u88C5\u2026",
      install_btn: "\u5F00\u59CB\u5B89\u88C5",
      install_btn_retry: "\u91CD\u8BD5",
      install_btn_running: "\u6B63\u5728\u5B89\u88C5...",
      install_complete: "\u2713 \u5B89\u88C5\u5B8C\u6210\uFF01",
      install_failed: "\u2717 \u5B89\u88C5\u5931\u8D25\uFF1A",
      install_validating:
        "\u6B63\u5728\u6821\u9A8C\u5B89\u88C5\u73AF\u5883\u2026",
      jump_to_deep_reading: "\u8DF3\u8F6C\u5230\u7CBE\u8BFB",
      label_agent: "Agent \u5E73\u53F0",
      nav_close: "\u5173\u95ED",
      nav_next: "\u4E0B\u4E00\u6B65 \u2192",
      nav_prev: "\u2190 \u4E0A\u4E00\u6B65",
      no_pending_ocr: "\u6240\u6709 OCR \u4EFB\u52A1\u5DF2\u5B8C\u6210",
      not_set: "\u672A\u8BBE\u7F6E",
      notice_check_fail: "\u672A\u901A\u8FC7: ",
      notice_python_missing:
        "Python \u672A\u68C0\u6D4B\u5230\uFF0C\u8BF7\u5148\u5B89\u88C5 Python 3.10+ \u5E76\u52A0\u5165 PATH",
      ocr_privacy_title: "OCR \u9690\u79C1\u63D0\u793A",
      ocr_privacy_warning:
        "OCR \u4F1A\u5C06 PDF \u4E0A\u4F20\u5230 PaddleOCR API \u8FDB\u884C\u5904\u7406\u3002\u8BF7\u4E0D\u8981\u4E0A\u4F20\u5305\u542B\u654F\u611F\u4FE1\u606F\u6216\u65E0\u6CD5\u5916\u4F20\u7684\u6587\u732E\u3002",
      ocr_queue_add: "\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_added: "\u5DF2\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_remove: "\u79FB\u51FA OCR \u961F\u5217",
      ocr_queue_removed: "\u5DF2\u79FB\u51FA OCR \u961F\u5217",
      ocr_understand: "\u6211\u4E86\u89E3\uFF0C\u7EE7\u7EED",
      optional_later:
        "\uFF08\u7A0D\u540E\u53EF\u5728\u8BBE\u7F6E\u4E2D\u8865\u5145\uFF09",
      orphan_delete_failed: "\u6E05\u7406\u5931\u8D25",
      orphan_delete_selected: "\u5220\u9664 {count} \u7BC7",
      orphan_deleted:
        "\u5DF2\u5220\u9664 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      orphan_desc:
        "\u8FD9\u4E9B\u6587\u732E\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002",
      orphan_deselect_all: "\u53D6\u6D88\u5168\u9009",
      orphan_explain:
        "\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002\u5DE5\u4F5C\u533A\u6587\u4EF6\u4ECD\u4FDD\u7559\u5728\u78C1\u76D8\u4E0A\u3002",
      orphan_keep_all: "\u4FDD\u7559\u5168\u90E8",
      orphan_none_selected: "\u672A\u9009\u62E9\u4EFB\u4F55\u6587\u732E",
      orphan_select_all: "\u5168\u9009",
      orphan_title: "\u53D1\u73B0 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      panel_actions: "\u5FEB\u6377\u64CD\u4F5C",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc:
        "Zotero \u2192 \u5DE5\u5177 \u2192 \u63D2\u4EF6 \u2192 \u5B89\u88C5 Better BibTeX",
      prep_export: "BBT \u81EA\u52A8\u5BFC\u51FA",
      prep_export_desc:
        "\u53F3\u952E\u6587\u732E\u5B50\u5206\u7C7B \u2192 \u5BFC\u51FA\u5206\u7C7B \u2192 BetterBibTeX JSON \u2192 \u52FE\u9009\u4FDD\u6301\u66F4\u65B0 \u2192 \u5BFC\u51FA\u5230\uFF08JSON \u6587\u4EF6\u540D\u5373\u4E3A Base \u540D\uFF09\uFF1A",
      prep_key: "PaddleOCR Key",
      prep_key_desc:
        "\u5728 https://aistudio.baidu.com/paddleocr \u83B7\u53D6 API Key",
      prep_python: "Python 3.10+",
      prep_python_desc:
        "\u786E\u4FDD Python \u53EF\u547D\u4EE4\u884C\u8C03\u7528\u3002\u70B9\u51FB\u4E0B\u65B9\u6309\u94AE\u81EA\u52A8\u68C0\u6D4B\u3002",
      prep_zotero: "Zotero \u684C\u9762\u7248",
      prep_zotero_desc: "\u5B89\u88C5 Zotero (https://www.zotero.org)",
      run_in_agent: "\u5728 {0} \u4E2D\u8FD0\u884C",
      runtime_health: "\u8FD0\u884C\u65F6\u72B6\u6001",
      runtime_health_checking: "\u6B63\u5728\u68C0\u6D4B\u2026",
      runtime_health_desc:
        "\u68C0\u67E5\u63D2\u4EF6\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u7684\u5339\u914D\u60C5\u51B5\uFF0C\u5E76\u786E\u8BA4\u5DF2\u90E8\u7F72\u7684 skill contract \u662F\u5426\u4E3A\u5F53\u524D\u7248\u672C\u3002",
      runtime_health_match: "\u5339\u914D",
      runtime_health_mismatch: "\u4E0D\u5339\u914D",
      runtime_health_package_ver: "Python \u5305 v{0}",
      runtime_health_plugin_ver: "\u63D2\u4EF6 v{0}",
      runtime_health_sync: "\u540C\u6B65\u8FD0\u884C\u65F6",
      runtime_health_sync_done:
        "\u8FD0\u884C\u65F6\u5DF2\u540C\u6B65\u81F3 v{0}",
      runtime_health_sync_fail:
        "\u8FD0\u884C\u65F6\u540C\u6B65\u5931\u8D25\uFF1A{0}",
      runtime_health_syncing: "\u6B63\u5728\u540C\u6B65\u2026",
      section_config: "\u5F53\u524D\u914D\u7F6E",
      section_guide: "\u64CD\u4F5C\u65B9\u5F0F",
      section_prep: "\u5B89\u88C5\u51C6\u5907",
      section_prep_desc:
        "\u9996\u6B21\u4F7F\u7528\u524D\uFF0C\u8BF7\u4F9D\u6B21\u5B8C\u6210\u4EE5\u4E0B\u51C6\u5907\uFF1A",
      setup_done:
        "\u2713 PaperForge \u73AF\u5883\u5DF2\u914D\u7F6E\u5B8C\u6210",
      setup_pending:
        "\u5C1A\u672A\u5B89\u88C5\uFF0C\u5B8C\u6210\u5B89\u88C5\u51C6\u5907\u540E\u70B9\u51FB\u5B89\u88C5\u5411\u5BFC",
      tab_features: "\u529F\u80FD",
      tab_setup: "\u5B89\u88C5",
      tab_maintenance: "\u7EF4\u62A4",
      validate_base: "Base \u76EE\u5F55\u672A\u586B\u5199",
      validate_fail: "\u914D\u7F6E\u9A8C\u8BC1\u5931\u8D25",
      validate_index: "\u7D22\u5F15\u76EE\u5F55\u672A\u586B\u5199",
      validate_key: "PaddleOCR API \u5BC6\u94A5\u672A\u586B\u5199",
      validate_notes: "\u6B63\u6587\u76EE\u5F55\u672A\u586B\u5199",
      validate_resources: "\u8D44\u6E90\u76EE\u5F55\u672A\u586B\u5199",
      validate_system: "\u7CFB\u7EDF\u76EE\u5F55\u672A\u586B\u5199",
      validate_vault: "Vault \u8DEF\u5F84\u672A\u586B\u5199",
      validate_zotero:
        "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879",
      wizard_agent_hint:
        "\u9009\u62E9\u4F60\u4F7F\u7528\u7684 AI Agent \u5E73\u53F0\uFF0C\u5B89\u88C5\u65F6\u5C06\u6309\u5BF9\u5E94\u683C\u5F0F\u90E8\u7F72\u6280\u80FD\u6587\u4EF6\uFF1A",
      wizard_dir_hint:
        "\u8D44\u6E90\u76EE\u5F55\u662F\u6587\u732E\u6570\u636E\u7684\u7EDF\u4E00\u6839\u76EE\u5F55\uFF0C\u4EE5\u4E0B\u5B50\u76EE\u5F55\u5C06\u521B\u5EFA\u5728\u5176\u5185\u90E8\uFF1A",
      wizard_dir_sub_hint:
        "\u8D44\u6E90\u76EE\u5F55\u5185\u7684\u4E24\u4E2A\u5B50\u76EE\u5F55\uFF1A",
      wizard_intro:
        "\u672C\u5411\u5BFC\u5C06\u5F15\u5BFC\u60A8\u5B8C\u6210 PaperForge \u73AF\u5883\u7684\u5B8C\u6574\u914D\u7F6E\u3002\u5B89\u88C5\u8FC7\u7A0B\u4F1A\u81EA\u52A8\u521B\u5EFA\u6240\u6709\u76EE\u5F55\u7ED3\u6784\uFF0C\u65E0\u9700\u624B\u52A8\u64CD\u4F5C\u3002",
      wizard_keys_hint:
        "\u4EE5\u4E0B\u4E3A API \u5BC6\u94A5\u4E0E Zotero \u914D\u7F6E\uFF1A",
      wizard_preview:
        "\u7CFB\u7EDF\u6587\u4EF6\u548C Agent \u914D\u7F6E\u4F4D\u4E8E Vault \u6839\u76EE\u5F55\u4E0B\u3002\u6587\u732E\u6570\u636E\uFF08\u6B63\u6587\u3001\u7D22\u5F15\uFF09\u7EDF\u4E00\u5B58\u653E\u5728\u8D44\u6E90\u76EE\u5F55\u5185\u3002\u5B89\u88C5\u540E\u4ECD\u53EF\u5728\u8BBE\u7F6E\u4E2D\u4FEE\u6539\u3002",
      wizard_safety:
        "\u5B89\u5168\u8BF4\u660E\uFF1A\u5982\u679C\u4F60\u9009\u62E9\u7684\u76EE\u5F55\u91CC\u5DF2\u7ECF\u6709\u6587\u4EF6\uFF0C\u5B89\u88C5\u5411\u5BFC\u4F1A\u4FDD\u7559\u5DF2\u6709\u5185\u5BB9\uFF0C\u53EA\u8865\u5145\u7F3A\u5931\u7684 PaperForge \u6587\u4EF6\u548C\u76EE\u5F55\u3002",
      wizard_step1: "\u6982\u89C8",
      wizard_step2: "\u76EE\u5F55",
      wizard_step3: "Agent",
      wizard_step4: "\u5B89\u88C5",
      wizard_step5: "\u5B8C\u6210",
      wizard_skip_ocr_desc:
        "OCR \u529F\u80FD\u5728\u914D\u7F6E\u6709\u6548\u7684 PaddleOCR API \u5BC6\u94A5\u4E4B\u524D\u4E0D\u53EF\u7528\u3002\u60A8\u53EF\u4EE5\u7EE7\u7EED\u5B8C\u6210\u8BBE\u7F6E\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_skip_ocr_continue:
        "\u7EE7\u7EED\uFF0C\u7A0D\u540E\u914D\u7F6E\u5BC6\u94A5",
      wizard_skip_ocr_back: "\u8FD4\u56DE\u914D\u7F6E",
      wizard_api_hint_skip:
        "OCR \u5BC6\u94A5\u4E3A\u9009\u586B\u9879 \u2014 \u53EF\u8DF3\u8FC7\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_sys_hint:
        "\u72EC\u7ACB\u4E8E\u8D44\u6E90\u76EE\u5F55\u7684\u7CFB\u7EDF\u6587\u4EF6\uFF1A",
      wizard_title: "PaperForge \u5B89\u88C5\u5411\u5BFC",
      ocr_maint_no_action: "\u65E0\u9700\u5904\u7406",
      ocr_maint_rebuild: "\u5EFA\u8BAE\u91CD\u5EFA",
      ocr_maint_failed: "OCR \u5931\u8D25",
      ocr_maint_limited: "\u7ED3\u679C\u4E00\u822C",
      ocr_maint_needs_attention: "\u9700\u8981\u5904\u7406",
      ocr_maint_limitations: "\u7ED3\u679C\u8BF4\u660E",
      ocr_maint_hero_ok: "OCR \u6574\u4F53\u6B63\u5E38\u3002",
      ocr_maint_hero_warn:
        "OCR \u9700\u8981\u5173\u6CE8\uFF1A{rebuild} \u7BC7\u5EFA\u8BAE\u91CD\u5EFA\uFF0C{failed} \u7BC7\u5904\u7406\u5931\u8D25\u3002",
      ocr_maint_hero_note:
        "\u672C\u9875\u53EA\u63D0\u793A\u7EF4\u62A4\u540E\u5927\u6982\u7387\u4F1A\u6539\u5584\u7684\u95EE\u9898\u3002\u90E8\u5206\u8BBA\u6587\u6548\u679C\u4E00\u822C\uFF0C\u7EF4\u62A4\u672A\u5FC5\u80FD\u6539\u5584\u3002",
      ocr_maint_limitations_intro:
        "\u8FD9\u7C7B\u8BBA\u6587\u901A\u5E38\u8868\u793A\u7248\u5F0F\u590D\u6742\u6216\u4FE1\u53F7\u504F\u5F31\uFF0CPaperForge \u76EE\u524D\u6CA1\u6709\u9AD8\u7F6E\u4FE1\u5EA6\u7684\u7EF4\u62A4\u5EFA\u8BAE\u3002",
      ocr_maint_all_papers: "\u5168\u90E8\u8BBA\u6587",
      ocr_maint_rebuild_btn: "\u91CD\u5EFA\u7ED3\u679C",
      maintenance_group_retry: "\u9700\u8981\u91CD\u8BD5",
      maintenance_group_rebuild: "\u53EF\u91CD\u5EFA\u7ED3\u679C",
      maintenance_group_legacy:
        "\u53EF\u5347\u7EA7\u65E7\u7ED3\u679C\uFF08\u53EF\u9009\uFF09",
      maintenance_btn_retry: "\u91CD\u8BD5",
      maintenance_btn_rebuild: "\u91CD\u5EFA",
      maintenance_btn_upgrade: "\u5347\u7EA7",
      maintenance_refresh_spinning: "\u6B63\u5728\u66F4\u65B0\u2026",
      maintenance_all_good: "\u2705 \u5168\u90E8\u6B63\u5E38",
      maintenance_n_pending: "{n} \u7BC7\u9700\u8981\u5904\u7406",
      version_panel_title: "\u7248\u672C\u5386\u53F2",
      version_panel_back: "\u8FD4\u56DE",
      version_filter_placeholder: "\u641C\u7D22\u8BBA\u6587...",
      version_papers_count: "{n} \u7BC7\u8BBA\u6587",
      version_current: "\u5F53\u524D",
      version_restore_btn: "\u6062\u590D",
      version_compare_btn: "\u5BF9\u6BD4",
      version_restore_selected: "\u6062\u590D\u9009\u4E2D\u7248\u672C",
      version_clear_old: "\u6E05\u9664\u65E7\u7248\u672C (\u91CA\u653E {size})",
      version_no_backups:
        "\u6CA1\u6709\u53EF\u6062\u590D\u7684\u5386\u53F2\u7248\u672C",
      version_restore_confirm:
        "\u786E\u8BA4\u5C06 {paper} \u6062\u590D\u5230 {label}\uFF1F",
      version_restore_done: "\u5DF2\u6062\u590D\u5230 {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} \u6BB5\u6709\u53D8\u5316",
      version_error_read: "\u65E0\u6CD5\u8BFB\u53D6\u7248\u672C\u6570\u636E",
    },
  },
  kr = null;
function Js(_) {
  try {
    let y = _.vault;
    if (typeof y.getConfig == "function") {
      let r = y.getConfig("language");
      if (r && String(r).startsWith("zh")) return "zh";
    }
  } catch (y) {}
  try {
    if (typeof localStorage != "undefined") {
      let y = localStorage.getItem("language");
      if (y && String(y).startsWith("zh")) return "zh";
    }
  } catch (y) {}
  return "en";
}
function kn(_) {
  kr = Js(_) === "zh" ? wr.zh : wr.en;
}
function f(_) {
  return (kr && kr[_]) || wr.en[_] || _;
}
var z = require("obsidian"),
  ie = ae(require("fs")),
  me = ae(require("path")),
  Vn = ae(require("os")),
  oe = require("child_process");
var qn = ae(Sr());
var Ve = ae(require("fs")),
  $e = ae(require("path")),
  Pn = ae(require("os")),
  Ke = require("child_process"),
  Pr = null,
  Sn = !1;
function re(_, y, r, n) {
  let i = r || Ve,
    a = n || Ke.execFileSync;
  if (y && y.python_path && y.python_path.trim()) {
    let u = y.python_path.trim();
    if (i.existsSync(u)) return { path: u, source: "manual", extraArgs: [] };
  }
  let c = [
    $e.join(_, ".paperforge-test-venv", "Scripts", "python.exe"),
    $e.join(_, ".venv", "Scripts", "python.exe"),
    $e.join(_, "venv", "Scripts", "python.exe"),
  ];
  for (let u of c)
    try {
      if (i.existsSync(u))
        return { path: u, source: "auto-detected", extraArgs: [] };
    } catch (p) {}
  let l = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let u of l)
    try {
      let p = a(u.path, [...u.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (p && p.toLowerCase().includes("python"))
        return {
          path: u.path,
          source: "auto-detected",
          extraArgs: u.extraArgs,
        };
    } catch (p) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function Cn(_, y, r, n, i) {
  n === void 0 && (n = 1e4);
  let a = i || Ke.execFile;
  return new Promise((c) => {
    a(
      _,
      ["-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: r, timeout: n },
      (l, u) => {
        if (l) {
          c({
            status: "not-installed",
            pyVersion: null,
            pluginVersion: y,
            error: l.message,
          });
          return;
        }
        let p = (u && u.trim()) || null;
        c(
          p === y
            ? { status: "match", pyVersion: p, pluginVersion: y, error: null }
            : {
                status: "mismatch",
                pyVersion: p,
                pluginVersion: y,
                error: null,
              }
        );
      }
    );
  });
}
function Fn(_, y, r) {
  r === void 0 && (r = []);
  let n = `paperforge==${y}`,
    i = `git+https://github.com/LLLin000/PaperForge.git@${y}`,
    a = [...r, "-m", "pip", "install", "--upgrade", n],
    c = [...r, "-m", "pip", "install", "--upgrade", i];
  return { cmd: _, url: i, args: c, pypiArgs: a, gitArgs: c, timeout: 12e4 };
}
function Rn(_, y, r, n, i, a) {
  let c = i || Ke.spawn;
  return new Promise((l) => {
    let u = Date.now(),
      p = { cwd: r, timeout: n, windowsHide: !0 };
    a && (p.env = a);
    let h = c(_, y, p),
      b = [],
      k = [];
    (h.stdout.on("data", (g) => {
      b.push(g.toString("utf-8"));
    }),
      h.stderr.on("data", (g) => {
        k.push(g.toString("utf-8"));
      }),
      h.on("close", (g) => {
        l({
          stdout: b.join(""),
          stderr: k.join(""),
          exitCode: g,
          elapsed: Date.now() - u,
        });
      }),
      h.on("error", (g) => {
        l({
          stdout: b.join(""),
          stderr:
            k.join("") +
            `
` +
            g.message,
          exitCode: -1,
          elapsed: Date.now() - u,
        });
      }));
  });
}
function Cr() {
  if (Sn) return Pr;
  Sn = !0;
  try {
    let _;
    if (process.platform === "win32") {
      let y = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      _ = (0, Ke.execFileSync)(y, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      _ = (0, Ke.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (_) {
      let y = _.split(
        `
`
      )[0].trim();
      y && (Pr = $e.dirname(y));
    }
  } catch (_) {}
  return Pr;
}
function ot() {
  let _ = { ...process.env },
    y = process.platform,
    r = Pn.homedir(),
    n = [],
    i = Cr();
  (i && n.push(i),
    y === "darwin"
      ? n.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${r}/.local/bin`
        )
      : y === "linux" &&
        n.push("/usr/local/bin", "/usr/bin", `${r}/.local/bin`));
  let a = _.PATH || "";
  return ((_.PATH = [...n, a].filter(Boolean).join($e.delimiter)), _);
}
function Tn(_) {
  return String(_)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function Fr(_) {
  if (!_) return !1;
  try {
    if (!Ve.existsSync(_)) return !1;
    for (let y of Ve.readdirSync(_)) if (Tn(y)) return !0;
  } catch (y) {}
  return !1;
}
function Jt(_) {
  if (!_) return !1;
  try {
    if (!Ve.existsSync(_)) return !1;
    for (let y of Ve.readdirSync(_)) {
      let r = $e.join(_, y, "extensions");
      try {
        if (!Ve.existsSync(r)) continue;
        for (let n of Ve.readdirSync(r)) if (Tn(n)) return !0;
      } catch (n) {}
    }
  } catch (y) {}
  return !1;
}
var lt = ae(require("fs")),
  he = ae(require("path")),
  Dn = require("child_process"),
  qe = null;
function Qs(_, y) {
  let r = y || lt,
    n = he.join(_, "paperforge.json"),
    i = {
      system_dir: "System",
      resources_dir: "Resources",
      literature_dir: "Literature",
      base_dir: "Bases",
    };
  try {
    if (!r.existsSync(n))
      return { ...i, _warning: "paperforge.json not found; using defaults" };
    let a = r.readFileSync(n, "utf-8"),
      c = JSON.parse(a),
      l = c.vault_config || {};
    return {
      system_dir: l.system_dir || c.system_dir || i.system_dir,
      resources_dir: l.resources_dir || c.resources_dir || i.resources_dir,
      literature_dir: l.literature_dir || c.literature_dir || i.literature_dir,
      base_dir: l.base_dir || c.base_dir || i.base_dir,
      _warning: null,
    };
  } catch (a) {
    return (
      console.warn(
        "PaperForge: Failed to read paperforge.json, using defaults",
        a
      ),
      { ...i, _warning: "paperforge.json invalid; using defaults" }
    );
  }
}
function Te(_, y) {
  let r = Qs(_, y),
    n = he.join(_, r.system_dir, "PaperForge");
  return {
    vault: _,
    systemDir: n,
    indexesDir: he.join(n, "indexes"),
    logsDir: he.join(n, "logs"),
    dbPath: he.join(n, "indexes", "paperforge.db"),
    memoryStatePath: he.join(n, "indexes", "memory-runtime-state.json"),
    vectorStatePath: he.join(n, "indexes", "vector-runtime-state.json"),
    healthStatePath: he.join(n, "indexes", "runtime-health.json"),
    buildStatePath: he.join(n, "indexes", "vector-build-state.json"),
    orphanStatePath: he.join(n, "indexes", "sync-orphan-state.json"),
    exportsDir: he.join(n, "exports"),
    ocrDir: he.join(n, "ocr"),
    pluginDataPath: he.join(
      _,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: he.join(_, "paperforge.json"),
    configWarning: r._warning,
  };
}
function Rr(_) {
  try {
    return lt.existsSync(_) ? JSON.parse(lt.readFileSync(_, "utf-8")) : null;
  } catch (y) {
    return null;
  }
}
function Xs(_) {
  let y = Te(_);
  return Rr(y.memoryStatePath);
}
function Rt(_) {
  let y = Te(_);
  return Rr(y.vectorStatePath);
}
function Tr(_) {
  let y = Te(_);
  return Rr(y.healthStatePath);
}
function An(_) {
  var r;
  let y = Tr(_);
  return !!(y && ((r = y.summary) == null ? void 0 : r.status) === "ok");
}
function Gt(_) {
  let y = Xs(_);
  return !y || y.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + y.paper_count_db + " | " + (y.fresh ? "fresh" : "stale");
}
function gt(_) {
  var n, i, a;
  let y = Rt(_);
  return y
    ? y.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((n = y.chunk_count) != null ? n : 0) +
          ((i = y.body_chunk_count) != null ? i : 0) +
          ((a = y.object_chunk_count) != null ? a : 0)) +
        " | " +
        y.model +
        " | " +
        y.mode
    : "Status unavailable";
}
function Ue(_, y) {
  if (qe) return qe;
  if (y && y.python_path && y.python_path.trim()) {
    let i = y.python_path.trim();
    if (lt.existsSync(i))
      return ((qe = { path: i, source: "manual", extraArgs: [] }), qe);
  }
  let r = [
    he.join(_, ".paperforge-test-venv", "Scripts", "python.exe"),
    he.join(_, ".venv", "Scripts", "python.exe"),
    he.join(_, "venv", "Scripts", "python.exe"),
  ];
  for (let i = 0; i < r.length; i++)
    if (lt.existsSync(r[i]))
      return (
        (qe = { path: r[i], source: "auto-detected", extraArgs: [] }),
        qe
      );
  let n = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let i = 0; i < n.length; i++)
    try {
      let a = n[i],
        c = (0, Dn.execFileSync)(a.path, a.extraArgs.concat(["--version"]), {
          encoding: "utf-8",
          timeout: 5e3,
          windowsHide: !0,
        });
      if (c && c.toLowerCase().indexOf("python") !== -1)
        return (
          (qe = {
            path: a.path,
            source: "auto-detected",
            extraArgs: a.extraArgs,
          }),
          qe
        );
    } catch (a) {}
  return (
    (qe = { path: "python", source: "auto-detected", extraArgs: [] }),
    qe
  );
}
function Dr(_, y, r) {
  return !_ ||
    typeof _ != "object" ||
    !Object.prototype.hasOwnProperty.call(_, y)
    ? !!r
    : !!_[y];
}
function Bn(_, y, r) {
  let n = !Dr(_, y, r);
  return (_ && typeof _ == "object" && (_[y] = n), n);
}
var xe = require("obsidian"),
  Me = ae(require("fs")),
  Mn = ae(require("path")),
  Ln = ae(require("https")),
  Dt = require("child_process");
function On(_, y) {
  return !y || !y.trim()
    ? { blocked: !0, reason: "zotero" }
    : _
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var Ar = class extends xe.Modal {
  constructor(r, n, i, a) {
    super(r);
    this._rowEls = [];
    ((this.orphans = n.map((c, l) => ({ ...c, _selected: !0, _idx: l }))),
      (this.vaultPath = i),
      (this.py = a));
  }
  _updateUI() {
    let r = this.orphans.filter((n) => n._selected);
    (this._countEl.setText(
      f("orphan_delete_selected").replace("{count}", String(r.length))
    ),
      this._selectAllBtn.setText(
        r.length === this.orphans.length
          ? f("orphan_deselect_all")
          : f("orphan_select_all")
      ));
    for (let n of this.orphans) {
      let i = this._rowEls[n._idx];
      i && i.toggleClass("paperforge-orphan-dimmed", !n._selected);
    }
  }
  onOpen() {
    let { contentEl: r } = this;
    (r.addClass("paperforge-modal"),
      r.createEl("h2", {
        text: f("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      r.createEl("p", { cls: "paperforge-modal-desc", text: f("orphan_desc") }),
      (this._rowEls = []));
    let n = r.createEl("div", { cls: "paperforge-orphan-list" });
    for (let a of this.orphans) {
      let c = n.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (a._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(c);
      let l = c.createEl("div", { cls: "paperforge-orphan-info" }),
        u = l.createEl("div", { cls: "paperforge-orphan-header" });
      u.createEl("span", {
        cls: "paperforge-orphan-key",
        text: a.citation_key || a.key,
      });
      let p = u.createEl("span", { cls: "paperforge-orphan-tags" });
      (p.createEl("span", {
        cls: "paperforge-tag " + (a.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: a.has_pdf ? "PDF" : "no PDF",
      }),
        a.collection_path &&
          p.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: a.collection_path,
          }),
        a.title &&
          l.createEl("div", { cls: "paperforge-orphan-title", text: a.title }));
      let h = [];
      (a.authors && h.push(a.authors),
        a.year && h.push(a.year),
        h.length > 0 &&
          l.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: h.join(" \xB7 "),
          }),
        l.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: f("orphan_explain"),
        }),
        c.addEventListener("click", () => {
          ((a._selected = !a._selected), this._updateUI());
        }));
    }
    let i = r.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = i.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let a = this.orphans.every((c) => c._selected);
        for (let c of this.orphans) c._selected = !a;
        this._updateUI();
      }),
      (this._countEl = i.createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: "Delete " + this.orphans.length + " selected",
      })),
      i
        .createEl("button", { cls: "paperforge-step-btn", text: "Keep all" })
        .addEventListener("click", () => this.close()),
      this._countEl.addEventListener("click", () => {
        let a = this.orphans.filter((l) => l._selected);
        if (a.length === 0) {
          new xe.Notice(f("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new xe.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let c = a.map((l) => l.key);
        (0, Dt.execFile)(
          this.py.path,
          [
            ...this.py.extraArgs,
            "-m",
            "paperforge",
            "--vault",
            this.vaultPath,
            "prune",
            "--force",
            "--json",
            ...c,
          ],
          { cwd: this.vaultPath, timeout: 6e4 },
          (l, u) => {
            if (l) {
              (new xe.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let p = JSON.parse(u),
                h = (p.data && p.data.deleted) || [];
              new xe.Notice("Deleted " + h.length + " orphan workspace(s)");
            } catch (p) {
              new xe.Notice("PaperForge: prune done");
            }
            this.close();
          }
        );
      }));
  }
  onClose() {
    this.contentEl.empty();
  }
};
function Qt(_, y, r) {
  console.log("[PF] checkOrphanState called");
  try {
    let i = Te(r).orphanStatePath;
    if (!Me.existsSync(i)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let a = Me.readFileSync(i, "utf-8"),
      l = JSON.parse(a).orphans || [];
    if ((console.log("[PF] orphans count:", l.length), l.length === 0)) return;
    let u = Ue(r, y.settings);
    (console.log("[PF] py.path:", u ? u.path : "null"),
      new Ar(_, l, r, u).open(),
      Me.unlinkSync(i),
      console.log("[PF] orphan file cleaned"));
  } catch (n) {
    console.log("[PF] checkOrphanState exception:", n.message || n);
  }
}
var Tt = class extends xe.Modal {
  constructor(r, n) {
    super(r);
    this._pendingSave = null;
    this._showSkipConfirm = !1;
    ((this.plugin = n), (this._step = 1));
  }
  onOpen() {
    this._render();
  }
  onClose() {
    this.contentEl.empty();
  }
  _render() {
    let { contentEl: r } = this;
    (r.empty(),
      r.addClass("paperforge-modal"),
      this._renderStepIndicator(),
      this._renderStepContent(),
      this._renderNavigation());
  }
  _renderStepIndicator() {
    let r = [
        f("wizard_step1"),
        f("wizard_step2"),
        f("wizard_step3"),
        f("wizard_step4"),
        f("wizard_step5"),
      ],
      n = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    r.forEach((i, a) => {
      let c = a + 1,
        l = n.createEl("div", {
          cls: `paperforge-step-dot ${c === this._step ? "active" : ""} ${c < this._step ? "done" : ""}`,
        });
      (l.createEl("span", { cls: "paperforge-step-num", text: `${c}` }),
        l.createEl("span", { cls: "paperforge-step-label", text: i }));
    });
  }
  _renderStepContent() {
    let r = this.contentEl.createEl("div", { cls: "paperforge-step-content" });
    switch (this._step) {
      case 1:
        this._stepOverview(r);
        break;
      case 2:
        this._stepDirectories(r);
        break;
      case 3:
        this._stepKeys(r);
        break;
      case 4:
        this._stepInstall(r);
        break;
      case 5:
        this._stepComplete(r);
        break;
    }
  }
  _renderNavigation() {
    let r = this.contentEl.createEl("div", { cls: "paperforge-step-nav" });
    (this._step > 1 &&
      r
        .createEl("button", { cls: "paperforge-step-btn", text: f("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? r
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: f("nav_next"),
            })
            .addEventListener("click", () => {
              if (this._step === 3) {
                let i = this._validateStep3();
                if (i.blocked) {
                  if (i.reason === "zotero") return;
                  if (i.reason === "ocr") {
                    ((this._showSkipConfirm = !0), this._render());
                    return;
                  }
                }
              }
              (this._step++, (this._showSkipConfirm = !1), this._render());
            })
        : r
            .createEl("button", {
              cls: "paperforge-step-btn",
              text: f("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let r = this.plugin.settings,
      n = On(this._apiKeyValidated, r.zotero_data_dir);
    if (n.reason === "ocr") return n;
    let i = (r.zotero_data_dir || "").trim();
    if (!i)
      return (
        new xe.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!Me.existsSync(i))
      return (
        new xe.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!Me.statSync(i).isDirectory())
      return (
        new xe.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let a = Mn.join(i, "storage");
    return !Me.existsSync(a) || !Me.statSync(a).isDirectory()
      ? (new xe.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(r) {
    (r.createEl("h2", { text: f("wizard_title") }),
      r.createEl("p", { text: f("wizard_intro") }));
    let n = this.plugin.settings,
      i = this.app.vault.adapter.basePath,
      a = r.createEl("div", { cls: "paperforge-dir-tree" }),
      c = a.createEl("div", { cls: "paperforge-dir-node root" });
    c.textContent = `\u{1F4C1} Vault (${i})`;
    let l = a.createEl("div", { cls: "paperforge-dir-children" }),
      u = l.createEl("div", { cls: "paperforge-dir-node folder" });
    ((u.textContent = `\u{1F4C1} ${n.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      u
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${n.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      l.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${n.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      l.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${n.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
      }),
      r.createEl("p", {
        text: f("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      r.createEl("p", {
        text: f("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let h = r.createEl("div", { cls: "paperforge-summary" }),
      b = [
        {
          label: f("dir_resources"),
          val: `${i}/${n.resources_dir || "Resources"}`,
        },
        {
          label: f("dir_notes"),
          val: `${i}/${n.resources_dir || "Resources"}/${n.literature_dir || "Literature"}`,
        },
        { label: f("dir_base"), val: `${i}/${n.base_dir || "Bases"}` },
        { label: f("dir_system"), val: `${i}/${n.system_dir || "System"}` },
      ];
    for (let k of b) {
      let g = h.createEl("div", { cls: "paperforge-summary-row" });
      (g.createEl("span", { cls: "paperforge-summary-label", text: k.label }),
        g.createEl("span", { cls: "paperforge-summary-value", text: k.val }));
    }
  }
  _stepDirectories(r) {
    (r.createEl("h2", { text: f("wizard_step2") }),
      r.createEl("p", { text: f("wizard_intro") }));
    let n = this.plugin.settings,
      i = this.app.vault.adapter.basePath;
    (this._modalField(r, f("dir_vault"), i, !0),
      r.createEl("p", {
        text: f("wizard_dir_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        r,
        "\u8D44\u6E90\u76EE\u5F55\uFF08\u521B\u5EFA\u6587\u732E\u5361\u7247\u76EE\u5F55\u7684\u5730\u65B9\uFF09",
        "resources_dir",
        n.resources_dir,
        "Resources"
      ),
      r.createEl("p", {
        text: f("wizard_dir_sub_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        r,
        "\u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08\u5B58\u653E\u6587\u732E\u5361\u7247\u7684\u5730\u65B9\uFF0CBase \u6570\u636E\u6765\u6E90\uFF09",
        "literature_dir",
        n.literature_dir,
        "Literature"
      ),
      r.createEl("p", {
        text: f("wizard_sys_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        r,
        "\u7CFB\u7EDF\u76EE\u5F55\uFF08\u5B58\u653E Zotero \u8F6F\u94FE\u63A5\u548C PaperForge \u7CFB\u7EDF\u6587\u4EF6\uFF09",
        "system_dir",
        n.system_dir,
        "System"
      ),
      this._modalInput(
        r,
        "Base \u76EE\u5F55\uFF08\u5B58\u653E\u6570\u636E\u7BA1\u7406\u9762\u677F\u7684\u5730\u65B9\uFF09",
        "base_dir",
        n.base_dir,
        "Bases"
      ),
      r.createEl("p", {
        text: f("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let a = r.createEl("div", { cls: "paperforge-summary" }),
      c = [
        { label: f("dir_resources"), val: `${i}/${n.resources_dir || ""}` },
        {
          label: f("dir_notes"),
          val: `${i}/${n.resources_dir || ""}/${n.literature_dir || ""}`,
        },
        { label: f("dir_system"), val: `${i}/${n.system_dir || ""}` },
        { label: f("dir_base"), val: `${i}/${n.base_dir || ""}` },
      ];
    for (let l of c) {
      let u = a.createEl("div", { cls: "paperforge-summary-row" });
      (u.createEl("span", { cls: "paperforge-summary-label", text: l.label }),
        u.createEl("span", { cls: "paperforge-summary-value", text: l.val }));
    }
  }
  _stepKeys(r) {
    if (
      (r.createEl("h2", { text: f("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(r);
      return;
    }
    let n = this.plugin.settings;
    r.createEl("p", {
      text: f("wizard_agent_hint"),
      cls: "paperforge-modal-hint",
    });
    let i = [
        { key: "opencode", name: "OpenCode" },
        { key: "claude", name: "Claude Code" },
        { key: "cursor", name: "Cursor" },
        { key: "github_copilot", name: "GitHub Copilot" },
        { key: "windsurf", name: "Windsurf" },
        { key: "codex", name: "Codex" },
        { key: "gemini", name: "Gemini CLI" },
        { key: "cline", name: "Cline" },
      ],
      a = r.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", {
      cls: "paperforge-modal-label",
      text: f("label_agent"),
    });
    let c = a.createEl("select", { cls: "paperforge-modal-select" });
    for (let k of i) {
      let g = c.createEl("option", { text: k.name, attr: { value: k.key } });
      k.key === (n.agent_platform || "opencode") && (g.selected = !0);
    }
    (c.addEventListener("change", () => {
      ((n.agent_platform = c.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      r.createEl("p", {
        text: f("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let l = r.createEl("div", { cls: "paperforge-modal-field" });
    l.createEl("label", {
      cls: "paperforge-modal-label",
      text: f("field_paddleocr"),
    });
    let u = l.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: "API Key" },
    });
    ((u.value = n.paddleocr_api_key || ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = l.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let p = l.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (p.addEventListener("click", () => this._validateApiKey(u.value, p)),
      u.addEventListener("input", () => {
        ((n.paddleocr_api_key = u.value),
          (this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      r.createEl("p", {
        text: f("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let h = r.createEl("div", { cls: "paperforge-modal-field" });
    h.createEl("label", {
      cls: "paperforge-modal-label",
      text: f("field_zotero_data"),
    });
    let b = h.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: f("field_zotero_placeholder") },
    });
    ((b.value = n.zotero_data_dir || ""),
      b.addEventListener("input", () => {
        ((n.zotero_data_dir = b.value),
          this._pendingSave && clearTimeout(this._pendingSave),
          (this._pendingSave = setTimeout(() => {
            (this.plugin.saveSettings(), (this._pendingSave = null));
          }, 500)));
      }));
  }
  _validateApiKey(r, n) {
    if (!r || r.length < 10) {
      ((this._apiKeyStatus.textContent =
        "\u5BC6\u94A5\u683C\u5F0F\u4E0D\u6B63\u786E\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"));
      return;
    }
    ((n.disabled = !0),
      (n.textContent = "\u9A8C\u8BC1\u4E2D\u2026"),
      (this._apiKeyStatus.textContent = "\u6B63\u5728\u9A8C\u8BC1\u2026"),
      (this._apiKeyStatus.className = "paperforge-apikey-status"));
    let i = JSON.stringify({ model: "PaddleOCR-VL-1.5" }),
      a = {
        hostname: "paddleocr.aistudio-app.com",
        path: "/api/v2/ocr/jobs",
        method: "POST",
        headers: {
          Authorization: "bearer " + r,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(i),
        },
        timeout: 1e4,
      },
      c = Ln.request(a, (l) => {
        ((n.disabled = !1), (n.textContent = "\u9A8C\u8BC1"));
        let u = "";
        (l.on("data", (p) => (u += p)),
          l.on("end", () => {
            try {
              let p = JSON.parse(u);
              l.statusCode === 400 && p.code === 10001
                ? ((this._apiKeyStatus.textContent =
                    "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0))
                : l.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      l.statusCode +
                      "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1));
            } catch (p) {
              ((this._apiKeyStatus.textContent =
                "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                (this._apiKeyStatus.className =
                  "paperforge-apikey-status error"),
                (this._apiKeyValidated = !1));
            }
          }));
      });
    (c.on("error", (l) => {
      ((n.disabled = !1),
        (n.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          l.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      c.write(i),
      c.end());
  }
  _renderSkipConfirm(r) {
    r.createEl("p", {
      text: f("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let n = r.createEl("div", { cls: "paperforge-modal-actions" });
    (n
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: f("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      n
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: f("wizard_skip_ocr_back"),
        })
        .addEventListener("click", () => {
          ((this._showSkipConfirm = !1), this._render());
        }));
  }
  _modalField(r, n, i, a) {
    let c = r.createEl("div", { cls: "paperforge-modal-field" });
    c.createEl("label", { cls: "paperforge-modal-label", text: n });
    let l = c.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((l.value = i), (l.disabled = !!a));
  }
  _modalInput(r, n, i, a, c) {
    let l = r.createEl("div", { cls: "paperforge-modal-field" });
    l.createEl("label", { cls: "paperforge-modal-label", text: n });
    let u = l.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: c || "" },
    });
    u.value = a;
    let p = this.plugin.settings;
    u.addEventListener("input", () => {
      ((p[i] = u.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(r, n, i, a, c) {
    let l = r.createEl("div", { cls: "paperforge-modal-field" });
    l.createEl("label", { cls: "paperforge-modal-label", text: n });
    let u = l.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: c || "" },
    });
    u.value = a;
    let p = this.plugin.settings;
    u.addEventListener("input", () => {
      ((p[i] = u.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(r) {
    (r.createEl("h2", { text: f("wizard_step4") }),
      (this._installLog = r.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let n = r.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: f("install_btn"),
    });
    n.addEventListener("click", () => this._runInstall(n));
  }
  async _runInstall(r) {
    var l, u, p, h, b, k;
    ((r.disabled = !0),
      (r.textContent = f("install_btn_running")),
      this._installLog.setText(
        f("install_validating") +
          `
`
      ),
      this._log(f("install_validating")));
    let n = this.plugin.settings,
      i = this._validate();
    if (i.length > 0) {
      (this._log(f("validate_fail") + ":"),
        i.forEach((g) => this._log("  \u2717 " + g)),
        (r.disabled = !1),
        (r.textContent = f("install_btn_retry")));
      return;
    }
    let a = (g, x = {}) =>
        new Promise((C, R) => {
          let { path: S, extraArgs: F = [] } = re(
              n.vault_path.trim(),
              this.plugin.settings,
              void 0,
              void 0
            ),
            B = (0, Dt.spawn)(S, [...F, ...g], {
              cwd: n.vault_path.trim(),
              env: ot(),
              timeout: 12e4,
              ...x,
            }),
            A = "",
            v = "";
          (B.stdout.on("data", (w) => {
            let O = w.toString("utf-8");
            ((A += O), x.logStdout && this._processSetupOutput(O));
          }),
            B.stderr.on("data", (w) => {
              let O = w.toString("utf-8");
              ((v += O), this._log("[stderr] " + O.trim()));
            }),
            B.on("close", (w) => {
              w === 0
                ? C({ stdout: A, stderr: v })
                : R(new Error(v.trim() || A.trim() || `exit code ${w}`));
            }),
            B.on("error", (w) => R(w)));
        }),
      c = [
        "-m",
        "paperforge",
        "--vault",
        n.vault_path.trim(),
        "setup",
        "--headless",
        "--system-dir",
        n.system_dir.trim(),
        "--resources-dir",
        n.resources_dir.trim(),
        "--literature-dir",
        n.literature_dir.trim(),
        "--base-dir",
        n.base_dir.trim(),
        "--agent",
        n.agent_platform || "opencode",
      ];
    (n.zotero_data_dir &&
      n.zotero_data_dir.trim() &&
      c.push("--zotero-data", n.zotero_data_dir.trim()),
      n.paddleocr_api_key &&
        n.paddleocr_api_key.trim() &&
        c.push("--paddleocr-key", n.paddleocr_api_key.trim()));
    try {
      let g = !0;
      try {
        await a(["-c", "import paperforge"]);
      } catch (x) {
        g = !1;
      }
      if (!g) {
        this._log(f("install_bootstrapping"));
        let x = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${x}`);
        let C = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && C.push("--user"),
          C.push(`paperforge==${x}`));
        try {
          await a(C, { logStdout: !0 });
        } catch (R) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${x}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (l = R.message) == null ? void 0 : l.slice(0, 200)
            ));
          let S = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && S.push("--user"),
            S.push(`git+https://github.com/LLLin000/PaperForge.git@v${x}`),
            await a(S, { logStdout: !0 }));
        }
      }
      (await a(c, { logStdout: !0, env: ot() }),
        this._log(f("install_complete")),
        (n.setup_complete = !0),
        await this.plugin.saveSettings(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (g) {
      console.error("PaperForge setup failed:", g.message);
      let x = this._formatSetupError(g.message);
      this._log(f("install_failed") + x);
      let C =
        (u = this._installLog.parentElement) == null
          ? void 0
          : u.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: f("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (C) {
        let R = g.message,
          S =
            ((h = (p = this.plugin) == null ? void 0 : p.settings) == null
              ? void 0
              : h.python_path) || "auto",
          F =
            ((k = (b = this.plugin) == null ? void 0 : b.manifest) == null
              ? void 0
              : k.version) || "?",
          B = process.platform + " " + process.arch,
          A,
          v;
        try {
          A = Cr() || "(not found)";
        } catch (I) {
          A = "(error)";
        }
        try {
          v = re(n.vault_path.trim(), this.plugin.settings, void 0, void 0);
        } catch (I) {
          v = null;
        }
        let w = (process.env.PATH || "").length,
          O = (process.env.PATH || "").toLowerCase().includes("git"),
          M = [
            "[PaperForge Diagnostic]",
            "Category: " + x,
            "Plugin version: " + F,
            "Python: " + S,
            "Resolved Python: " + ((v == null ? void 0 : v.path) || "?"),
            "OS: " + B,
            "Vault path: " + (n.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + A,
            "PATH length: " + w + " chars",
            "PATH contains git: " + O,
            "--- Raw error ---",
            R.slice(0, 2e3),
          ].join(`
`);
        C.addEventListener("click", () => {
          navigator.clipboard
            .writeText(M)
            .then(() => {
              (C.setText(f("error_copied") || "Copied!"),
                setTimeout(() => {
                  C.setText(f("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new xe.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((r.disabled = !1), (r.textContent = f("install_btn_retry")));
    }
  }
  _log(r) {
    this._installLog &&
      this._installLog.setText(
        this._installLog.textContent +
          r +
          `
`
      );
  }
  _validate() {
    let r = [],
      n = this.plugin.settings;
    return (
      (!n.vault_path || !n.vault_path.trim()) && r.push(f("validate_vault")),
      (!n.resources_dir || !n.resources_dir.trim()) &&
        r.push(f("validate_resources")),
      (!n.literature_dir || !n.literature_dir.trim()) &&
        r.push(f("validate_notes")),
      (!n.base_dir || !n.base_dir.trim()) && r.push(f("validate_base")),
      (!n.paddleocr_api_key || !n.paddleocr_api_key.trim()) &&
        this._log("  ! " + f("validate_key") + " " + f("optional_later")),
      (!n.zotero_data_dir || !n.zotero_data_dir.trim()) &&
        this._log("  ! " + f("validate_zotero") + " " + f("optional_later")),
      r
    );
  }
  _processSetupOutput(r) {
    let n = r
      .split(
        `
`
      )
      .filter(Boolean);
    for (let i of n)
      if (i.includes("[*]") || i.includes("[OK]") || i.includes("[FAIL]")) {
        let a = i
          .replace(/^\[\*\].*\d+:?\s*/, "")
          .replace(/^\[OK\]\s*/, "")
          .replace(/^\[FAIL\]\s*/, "");
        this._log("  " + a);
      }
  }
  _formatSetupError(r) {
    if (
      process.platform === "darwin" &&
      /No module named ['"]?paperforge/i.test(r)
    )
      return "PaperForge not installed \u2014 install Python from Homebrew or python.org (Apple CLT /Library/Developer/CommandLineTools python often fails); then: python3 -m pip install --user git+https://github.com/LLLin000/PaperForge.git";
    let n = [
      {
        match: /pip.*not found|No module named.*pip|command not found.*pip/i,
        msg: "pip not found",
      },
      {
        match: /command not found|No such file|not recognized/i,
        msg: "Python not found",
      },
      {
        match:
          /resolve host|getaddrinfo.*nodename|connect ETIMEDOUT|connect ECONNREFUSED|fetch failed|Network error|ENOTFOUND|ECONNREFUSED|ECONNRESET/i,
        msg: "Network error",
      },
      {
        match:
          /certificate verify failed|SSL.*certificate|self.signed.cert|CERTIFICATE_VERIFY_FAILED/i,
        msg: "SSL certificate error",
      },
      { match: /No space left on device|disk full|ENOSPC/i, msg: "Disk full" },
      {
        match:
          /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i,
        msg: "PaperForge not installed",
      },
      { match: /permission denied|EACCES|EPERM/i, msg: "Permission denied" },
      { match: /ENOENT/i, msg: "Path not found" },
      { match: /timeout|timed out/i, msg: "Timeout" },
    ];
    for (let a of n) if (a.match.test(r)) return a.msg;
    return (
      r
        .split(
          `
`
        )
        .filter(Boolean)
        .slice(0, 3)
        .join(" | ")
        .slice(0, 200) || "Unknown error"
    );
  }
  _stepComplete(r) {
    r.createEl("h2", { text: f("complete_title") });
    let n = r.createEl("div", { cls: "paperforge-summary" });
    n.createEl("div", {
      cls: "paperforge-summary-title",
      text: f("complete_summary"),
    });
    let i = this.plugin.settings,
      a = this.app.vault.adapter.basePath,
      c = [
        { label: f("dir_vault"), val: a },
        { label: f("dir_resources"), val: `${a}/${i.resources_dir}` },
        {
          label: f("dir_notes"),
          val: `${a}/${i.resources_dir}/${i.literature_dir}`,
        },
        { label: f("dir_base"), val: `${a}/${i.base_dir}` },
        { label: f("dir_system"), val: `${a}/${i.system_dir}` },
        {
          label: "API Key",
          val: i.paddleocr_api_key ? f("api_key_set") : f("api_key_missing"),
        },
        {
          label: f("field_zotero_data"),
          val: i.zotero_data_dir || f("not_set"),
        },
      ];
    for (let b of c) {
      let k = n.createEl("div", { cls: "paperforge-summary-row" });
      (k.createEl("span", { cls: "paperforge-summary-label", text: b.label }),
        k.createEl("span", { cls: "paperforge-summary-value", text: b.val }));
    }
    let l = n.createEl("div", { cls: "paperforge-summary-row" });
    l.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let u = l.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let b = a,
        { path: k, extraArgs: g = [] } = re(
          b,
          this.plugin.settings,
          void 0,
          void 0
        );
      (0, Dt.execFile)(
        k,
        [...g, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: b, timeout: 1e4 },
        (x, C) => {
          !x && C && (u.textContent = "v" + C.trim());
        }
      );
    }
    for (let b of c) {
      let k = n.createEl("div", { cls: "paperforge-summary-row" });
      (k.createEl("span", { cls: "paperforge-summary-label", text: b.label }),
        k.createEl("span", { cls: "paperforge-summary-value", text: b.val }));
    }
    r.createEl("h3", { text: f("complete_next") });
    let p = r.createEl("div", { cls: "paperforge-nextsteps" }),
      h = [
        [f("complete_step4"), f("complete_step4_desc")],
        [
          "",
          `${f("complete_export_path")} ${a}/${i.system_dir}/PaperForge/exports/`,
        ],
        [f("complete_step1"), f("complete_step1_desc")],
        [f("complete_step2"), f("complete_step2_desc")],
        [f("complete_step3"), f("complete_step3_desc")],
      ];
    for (let [b, k] of h) {
      let g = p.createEl("div", { cls: "paperforge-nextstep-item" });
      (b && g.createEl("strong", { text: b }), g.createEl("span", { text: k }));
    }
  }
};
var _t = ae(require("fs")),
  Xt = ae(require("path")),
  Nn = require("child_process");
function jn(_) {
  return Xt.join(_, "System", "PaperForge", "cache", "ocr_maintenance.json");
}
function zn(_) {
  try {
    let y = jn(_),
      r = _t.readFileSync(y, "utf-8");
    return JSON.parse(r);
  } catch (y) {
    return null;
  }
}
function Yt(_, y) {
  let r = jn(_),
    n = Xt.dirname(r);
  (_t.mkdirSync(n, { recursive: !0 }),
    _t.writeFileSync(r, JSON.stringify(y, null, 2), "utf-8"));
}
function In(_, y, r) {
  return new Promise((n, i) => {
    (0, Nn.execFile)(_, y, r, (a, c) => {
      a ? i(a) : n(c);
    });
  });
}
async function $n(_, y, r, n) {
  let i = await In(y, [...r, "-m", "paperforge", "ocr", "list", "--manifest"], {
      cwd: _,
      timeout: 3e4,
    }),
    a = JSON.parse(i);
  if (n) {
    let b = Object.keys(n.manifest),
      k = Object.keys(a);
    if (b.length === k.length && b.every((x) => n.manifest[x] === a[x]))
      return {
        data: Object.values(n.papers).filter((C) => C.visible_in_maintenance),
        changed: !1,
      };
  }
  let c = Object.keys(a).filter(
      (b) => !(n != null && n.manifest[b]) || n.manifest[b] !== a[b]
    ),
    l = await In(
      y,
      [...r, "-m", "paperforge", "ocr", "list", "--json", "--keys", ...c],
      { cwd: _, timeout: 3e4 }
    ),
    u = JSON.parse(l),
    p = { manifest: a, papers: {}, cached_at: new Date().toISOString() };
  if (n != null && n.papers)
    for (let b of Object.keys(a)) n.papers[b] && (p.papers[b] = n.papers[b]);
  for (let b of u) p.papers[b.key] = b;
  return (
    Yt(_, p),
    {
      data: Object.values(p.papers).filter((b) => b.visible_in_maintenance),
      changed: !0,
    }
  );
}
var er = class extends z.PluginSettingTab {
  constructor(r, n) {
    super(r, n);
    this._saveTimeout = null;
    this._pfConfig = null;
    this._lastSyncTime = null;
    this._memoryStatusText = null;
    this._vectorDepsOk = null;
    this._embedStatusText = null;
    this._skillsCollapsed = { user: !0 };
    this._featurePanelsCollapsed = {};
    this._advCollapsed = !0;
    this._refreshPending = !1;
    this._pythonInterpDescEl = null;
    this._customPathDescEl = null;
    this._checkEl = null;
    this.activeTab = "setup";
    this.plugin = n;
  }
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }
  display() {
    let { containerEl: r } = this;
    if (
      (r.empty(),
      this._refreshPfConfig(),
      !document.getElementById("paperforge-tab-styles"))
    ) {
      let c = document.createElement("style");
      ((c.id = "paperforge-tab-styles"),
        (c.textContent = `
                .paperforge-settings-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--background-modifier-border); }
                .paperforge-settings-tab { padding: 6px 16px; border: none; background: none; cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; color: var(--text-muted); }
                .paperforge-settings-tab--active { color: var(--text-accent); border-bottom-color: var(--text-accent); }
                .paperforge-tab-content { display: none; }
                .paperforge-tab-content--active { display: block; }
                .paperforge-skills-collapse-header { display: flex !important; align-items: center; cursor: pointer; padding: 6px 0 !important; margin: 0 !important; }
                .paperforge-skills-collapse-header h4 { margin: 0 !important; }
                .paperforge-skills-collapse-content { margin: 0 !important; padding: 0 !important; }
                .paperforge-skills-group { margin-bottom: 10px; }
                .paperforge-skills-group:last-child { margin-bottom: 0; }
                .vertical-tab-content-container { overflow-y: scroll !important; }
                .paperforge-release-card { border: 1px solid var(--background-modifier-border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
                .paperforge-release-header { margin-bottom: 8px; }
                .paperforge-release-date { color: var(--text-muted); font-size: 12px; }
                .paperforge-release-section { margin-bottom: 6px; }
                .paperforge-release-label { font-weight: 600; color: var(--text-accent); margin-bottom: 2px; font-size: 13px; }
                .paperforge-release-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-release-item-bold { font-size: 13px; margin-left: 8px; font-weight: 600; color: var(--text-normal); }
                .paperforge-release-recommended { background: rgba(var(--color-orange-rgb, 255,166,0), 0.08); border-radius: 4px; padding: 6px 8px; }
                .paperforge-manual-links { margin-top: 8px; }
                .paperforge-manual-links a { color: var(--text-accent); }
                .paperforge-modal-subtitle { color: var(--text-muted); font-size: 13px; margin-bottom: 12px; }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
            `),
        document.head.appendChild(c));
    }
    let n = r.createDiv({ cls: "paperforge-settings-tabs" }),
      i = [
        { id: "setup", label: f("tab_setup") || "\u5B89\u88C5" },
        { id: "features", label: f("tab_features") || "\u529F\u80FD" },
        { id: "maintenance", label: f("tab_maintenance") || "\u7EF4\u62A4" },
        { id: "release-notes", label: "\u66F4\u65B0\u4E0E\u624B\u518C" },
      ],
      a = {};
    (i.forEach((c) => {
      n.createEl("button", {
        cls:
          "paperforge-settings-tab" +
          (c.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
        text: c.label,
      }).addEventListener("click", () => {
        ((this.activeTab = c.id), this.display());
      });
    }),
      i.forEach((c) => {
        a[c.id] = r.createDiv({
          cls:
            "paperforge-tab-content" +
            (c.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      this.activeTab === "setup"
        ? this._renderSetupTab(a.setup)
        : this.activeTab === "features"
          ? this._renderFeaturesTab(a.features)
          : this.activeTab === "maintenance"
            ? this._renderMaintenanceTab(a.maintenance)
            : this._renderReleaseNotesTab(a["release-notes"]));
  }
  _renderSetupTab(r) {
    let n = this.app.vault.adapter.basePath;
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = n), this._debouncedSave()),
      this.plugin.settings.setup_complete &&
        (ie.existsSync(me.join(n, "paperforge.json")) ||
          ((this.plugin.settings.setup_complete = !1), this._debouncedSave())),
      r.createEl("h2", { text: f("header_title") || "PaperForge" }),
      r.createEl("p", { text: f("desc"), cls: "paperforge-settings-desc" }));
    let a = r
      .createEl("div", { cls: "paperforge-setup-bar" })
      .createEl("span", { cls: "paperforge-setup-label" });
    this.plugin.settings.setup_complete
      ? (a.setText(f("setup_done")), a.addClass("paperforge-setup-done"))
      : (a.setText(f("setup_pending")), a.addClass("paperforge-setup-pending"));
    let c = this.app.vault.adapter.basePath,
      l = re(c, this.plugin.settings, void 0, void 0),
      u = l.path,
      p = this.plugin.settings._python_path_stale ? "stale" : l.source,
      h = new z.Setting(r)
        .setName(f("field_python_interp"))
        .setDesc(this._getPythonDesc(u, p));
    this._pythonInterpDescEl = h.descEl;
    let b = new z.Setting(r).setName(f("field_python_custom")).setDesc("");
    ((this._customPathDescEl = b.descEl),
      b.addText((A) => {
        A.setPlaceholder("e.g. C:\\Python310\\python.exe")
          .setValue(this.plugin.settings.python_path || "")
          .onChange((v) => {
            if (
              ((this.plugin.settings.python_path = v),
              this.plugin.saveSettings(),
              v && v.trim())
            ) {
              let M = ie.existsSync(v.trim());
              this.plugin.settings._python_path_stale = !M;
            } else this.plugin.settings._python_path_stale = !1;
            let w = re(
                this.app.vault.adapter.basePath,
                this.plugin.settings,
                void 0,
                void 0
              ),
              O = this.plugin.settings._python_path_stale ? "stale" : w.source;
            this._pythonInterpDescEl &&
              (this._pythonInterpDescEl.textContent = this._getPythonDesc(
                w.path,
                O
              ));
          });
      }),
      b.addButton((A) => {
        A.setButtonText(f("btn_validate")).onClick(() =>
          this._validatePythonOverride()
        );
      }),
      r.createEl("h3", { text: f("runtime_health") }),
      r.createEl("p", {
        text: f("runtime_health_desc"),
        cls: "paperforge-settings-desc",
      }));
    let k = new z.Setting(r)
        .setName("PaperForge")
        .setDesc(f("runtime_health_checking")),
      g = k.descEl.createEl("span", { cls: "paperforge-runtime-badge" }),
      x = null;
    k.addButton((A) => {
      ((x = A),
        A.setButtonText(f("runtime_health_sync"))
          .setDisabled(!0)
          .onClick(() => this._syncRuntime(A)));
    });
    {
      let A = this.app.vault.adapter.basePath,
        { path: v, extraArgs: w = [] } = re(
          A,
          this.plugin.settings,
          void 0,
          void 0
        ),
        O = this.plugin.manifest.version || "?";
      (0, oe.execFile)(
        v,
        [...w, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: A, timeout: 1e4 },
        (M, I) => {
          let J = this.plugin.settings.setup_complete,
            q = !M && I ? I.trim() : null,
            te = q
              ? `${f("runtime_health_plugin_ver").replace("{0}", O)} \u2192 ${f("runtime_health_package_ver").replace("{0}", q)}`
              : J
                ? `Plugin v${O} \u2192 Python package not installed. Click "Sync Runtime" to install.`
                : `Plugin v${O} \u2192 Not configured. Please open the setup wizard first.`;
          (k.setDesc(te),
            q === O
              ? (g.setText(f("runtime_health_match")),
                (g.className = "paperforge-runtime-badge match"),
                x && x.setDisabled(!0))
              : q
                ? (g.setText(f("runtime_health_mismatch")),
                  (g.className = "paperforge-runtime-badge mismatch"),
                  x && x.setDisabled(!1))
                : (g.setText(J ? "Not installed" : "Setup needed"),
                  (g.className = "paperforge-runtime-badge missing"),
                  x && x.setDisabled(!1)));
        }
      );
    }
    (r.createEl("h3", { text: f("section_prep") }),
      r.createEl("p", {
        text: f("section_prep_desc"),
        cls: "paperforge-settings-desc",
      }));
    let C = r.createEl("div", { cls: "paperforge-guide" }),
      R = [
        ["prep_python", "prep_python_desc"],
        ["prep_zotero", "prep_zotero_desc"],
        ["prep_bbt", "prep_bbt_desc"],
        ["prep_key", "prep_key_desc"],
      ];
    for (let [A, v] of R) {
      let w = C.createEl("div", { cls: "paperforge-guide-item" });
      (w.createEl("strong", { text: f(A) }),
        w.createEl("span", { text: " \u2014 " + f(v) }));
    }
    this._checkEl = r.createEl("div", { cls: "paperforge-message" });
    let S = !this.plugin.settings.setup_complete;
    (new z.Setting(r)
      .setName(f(S ? "btn_install" : "btn_reconfig"))
      .setDesc(f(S ? "btn_install_desc" : "btn_reconfig_desc"))
      .addButton((A) => {
        A.setButtonText(f(S ? "btn_install" : "btn_reconfig"))
          .setCta()
          .onClick(() => {
            S
              ? this._preCheck(() => {
                  new Tt(this.app, this.plugin).open();
                })
              : new Tt(this.app, this.plugin).open();
          });
      }),
      r.createEl("h3", { text: f("section_guide") }));
    let F = r.createEl("div", { cls: "paperforge-guide" }),
      B = [
        ["guide_open", "guide_open_desc"],
        ["guide_sync", "guide_sync_desc"],
        ["guide_ocr", "guide_ocr_desc"],
      ];
    for (let [A, v] of B) {
      let w = F.createEl("div", { cls: "paperforge-guide-item" });
      (w.createEl("strong", { text: f(A) }),
        w.createEl("span", { text: " \u2014 " + f(v) }));
    }
    if (this.plugin.settings.setup_complete) {
      r.createEl("h3", { text: f("section_config") });
      let A = r.createEl("div", { cls: "paperforge-summary" }),
        v = this.plugin.settings,
        w = this._pfConfig,
        O = [
          { label: f("dir_vault"), val: n },
          {
            label: f("dir_resources"),
            val: `${n}/${w == null ? void 0 : w.resources_dir}`,
          },
          {
            label: "  " + f("dir_notes"),
            val: `${n}/${w == null ? void 0 : w.resources_dir}/${w == null ? void 0 : w.literature_dir}`,
          },
          {
            label: f("dir_base"),
            val: `${n}/${w == null ? void 0 : w.base_dir}`,
          },
          {
            label: f("dir_system"),
            val: `${n}/${w == null ? void 0 : w.system_dir}`,
          },
          {
            label: "API Key",
            val: v.paddleocr_api_key ? f("api_key_set") : f("api_key_missing"),
          },
          {
            label: f("field_zotero_data"),
            val: v.zotero_data_dir || f("not_set"),
          },
        ];
      for (let M of O) {
        let I = A.createEl("div", { cls: "paperforge-summary-row" });
        (I.createEl("span", { cls: "paperforge-summary-label", text: M.label }),
          I.createEl("span", { cls: "paperforge-summary-value", text: M.val }));
      }
    }
  }
  _execMemoryStatus(r, n, i) {
    (0, oe.exec)(
      `"${r}" -m paperforge --vault "${n}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (a, c) => {
        if (a) {
          i("Status unavailable");
          return;
        }
        try {
          let l = JSON.parse(c);
          if (l.ok) {
            let u = l.data,
              p = u.fresh ? "fresh" : "stale";
            i(
              `Papers: ${u.paper_count_db} | ${p}${u.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else i("DB not found. Run paperforge memory build.");
        } catch (l) {
          i("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(r, n, i) {
    (0, oe.exec)(
      `"${r}" -m paperforge --vault "${n}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (a, c) => {
        if (a) {
          i("Status unavailable");
          return;
        }
        try {
          let l = JSON.parse(c);
          l.ok
            ? i(
                `Chunks: ${l.data.chunk_count} | ${l.data.model} | ${l.data.mode}`
              )
            : i("Could not parse status.");
        } catch (l) {
          i("Could not parse status.");
        }
      }
    );
  }
  _callPython(r, n) {
    let i = this.app.vault.adapter.basePath,
      a = Ue(i, this.plugin.settings),
      c = [...a.extraArgs, "-m", "paperforge", "--vault", i, ...r];
    if (n && n.stream) {
      let l = (0, oe.spawn)(a.path, c, {
        cwd: i,
        env: n.env || process.env,
        windowsHide: !0,
      });
      return (
        n.onData && l.stdout.on("data", n.onData),
        n.onStderr && l.stderr.on("data", n.onStderr),
        n.onError && l.on("error", n.onError),
        l.on("close", n.onClose),
        l
      );
    }
    return (
      (0, oe.execFile)(
        a.path,
        c,
        { cwd: i, timeout: (n && n.timeout) || 6e4 },
        (l, u, p) => {
          n && n.onClose && n.onClose(l ? 1 : 0, u, p);
        }
      ),
      null
    );
  }
  _renderMemoryStatusText(r, n, i) {
    ((r.innerHTML = ""),
      r.createEl("span", { text: n, cls: "paperforge-memory-text" }),
      i === "syncing"
        ? r.createEl("span", {
            text: "Syncing...",
            cls: "paperforge-sync-status",
          })
        : i && r.createEl("span", { text: i, cls: "paperforge-sync-status" }));
    let a = r.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: f("feat_memory_rebuild_btn"),
    });
    ((a.title = "Rebuild memory database"),
      (a.onclick = () => {
        let l = this.app.vault.adapter.basePath,
          u = Ue(l, this.plugin.settings);
        if (!u.path) {
          new z.Notice(f("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", u.path),
          a.setText(f("feat_memory_rebuilding")),
          a.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (p, h, b) => {
              (console.log(
                "[PaperForge] memory build exit:",
                p ? "FAIL:" + p : "OK",
                (h || "").slice(0, 200),
                (b || "").slice(0, 200)
              ),
                a.setText(f("feat_memory_rebuild_btn")),
                a.removeAttribute("disabled"),
                p === 0
                  ? new z.Notice(f("feat_memory_rebuild_done"))
                  : new z.Notice(
                      f("feat_memory_rebuild_failed") +
                        (b ? " " + b.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = Gt(l)),
                this._refreshSnapshots(l));
            },
          }));
      }));
    let c = r.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    ((c.title = "Sync now"),
      (c.onclick = () => {
        ((this._memoryStatusText = null), this._runManualSync());
      }));
  }
  _getBuildCommand(r) {
    let n = this.app.vault.adapter.basePath,
      i = re(n, r, void 0, void 0);
    return i.path ? `"${i.path}" -m paperforge --vault "${n}" sync` : null;
  }
  _runManualSync() {
    let r = this.app.vault.adapter.basePath;
    if (!Ue(r, this.plugin.settings).path) return;
    let i = document.querySelector(".paperforge-memory-status");
    (i && this._renderMemoryStatusText(i, "Checking...", "syncing"),
      (this.plugin._autoSyncRunning = !0),
      this._callPython(["sync"], {
        timeout: 12e4,
        onClose: (a) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._memoryStatusText = null),
            a === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this.display(),
            this._refreshSnapshots(r),
            Qt(this.app, this.plugin, r));
        },
      }));
  }
  _refreshSnapshots(r) {
    let n = Ue(r, this.plugin.settings),
      i = [
        ...n.extraArgs,
        "-m",
        "paperforge",
        "--vault",
        r,
        "runtime-health",
        "--json",
      ];
    ((this._refreshPending = !0),
      (0, oe.execFile)(
        n.path,
        i,
        { cwd: r, timeout: 3e4, windowsHide: !0 },
        (a, c, l) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = Gt(r)),
            (this._embedStatusText = gt(r)),
            this.display());
        }
      ));
  }
  _renderFeaturesTab(r) {
    r.createEl("h3", { text: "Skills" });
    let n = r.createEl("div", { cls: "paperforge-desc-box" });
    (n.setText(f("feat_skills_desc")),
      n.createEl("br"),
      n.createEl("span", { text: f("feat_skills_system") }));
    let i = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      a = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      c = this.app.vault.adapter.basePath,
      l = this.plugin.settings.selected_skill_platform || "opencode";
    new z.Setting(r)
      .setName(f("feat_agent_platform"))
      .setDesc(f("feat_agent_platform_desc"))
      .addDropdown((v) => {
        (Object.entries(i).forEach(([w, O]) => v.addOption(w, O)),
          v.setValue(l).onChange((w) => {
            ((this.plugin.settings.selected_skill_platform = w),
              this.plugin.saveSettings(),
              this.display());
          }));
      })
      .addExtraButton((v) => {
        v.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            let w = a[l] || ".opencode/skills",
              O = me.join(c, w);
            ie.existsSync(O)
              ? (0, oe.exec)(`start "" "${O}"`)
              : new z.Notice(`Skills folder not found: ${w}`);
          });
      });
    let u = me.join(c, a[l]),
      p = [],
      h = [];
    ie.existsSync(u) &&
      ie.readdirSync(u, { withFileTypes: !0 }).forEach((v) => {
        if (!v.isDirectory()) return;
        let w = me.join(u, v.name, "SKILL.md");
        if (!ie.existsSync(w)) return;
        let O = ie.readFileSync(w, "utf-8"),
          M = O.match(/^name:\s*(.+)$/m),
          I = O.split(`
`),
          J = I.findIndex((ue) => /^description:/.test(ue)),
          q = "";
        if (J >= 0) {
          let ue = I[J].match(/^description:\s*(.+)$/);
          if (ue && ue[1] && ue[1] !== ">" && ue[1] !== "|-" && ue[1] !== "|")
            q = ue[1].trim();
          else {
            for (
              let V = J + 1;
              V < I.length && (/^\s{2,}/.test(I[V]) || I[V].trim() === "");
              V++
            )
              q += I[V].trim() + " ";
            q = q.trim();
          }
        }
        let te = O.match(/^source:\s*(.+)$/m),
          se = O.match(/^disable-model-invocation:\s*(.+)$/m),
          G = O.match(/^version:\s*(.+)$/m),
          ye = {
            name: M ? M[1].trim() : v.name,
            desc: q,
            source: te ? te[1].trim() : "user",
            disabled: se && se[1].trim() === "true",
            version: G ? G[1].trim() : "",
            path: w,
            content: O,
            dirName: v.name,
          };
        ye.source === "paperforge" ? p.push(ye) : h.push(ye);
      });
    let b = r.createEl("div", { cls: "paperforge-skills-box" }),
      k = (v, w, O) => {
        if (w.length === 0) return;
        let M = b.createEl("div", { cls: "paperforge-skills-group" }),
          I = M.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          J = M.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          q = I.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (I.createEl("h4", {
          text: `${v} (${w.length})`,
          cls: "paperforge-skills-subheader",
        }),
          w.forEach((G) => {
            let ye = G.name + (G.version ? " v" + G.version : ""),
              ue = O ? " [system]" : " [user]",
              V = G.desc || "",
              U = new z.Setting(J).setName(ye + ue).setDesc(V);
            ((U.settingEl.style.opacity = G.disabled ? "0.4" : "1"),
              U.addToggle((be) => {
                be.setValue(!G.disabled).onChange((we) => {
                  let ge = !we,
                    fe = G.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? G.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${ge}`
                        )
                      : G.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${ge}
`
                        );
                  (ie.writeFileSync(G.path, fe, "utf-8"),
                    (G.disabled = ge),
                    (G.content = fe),
                    (U.settingEl.style.opacity = G.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let te = O ? "system" : "user";
        ((this._skillsCollapsed[te] || !1) &&
          ((J.style.display = "none"), (q.style.transform = "rotate(-90deg)")),
          I.addEventListener("click", () => {
            (J.style.display !== "none"
              ? ((J.style.display = "none"),
                (q.style.transform = "rotate(-90deg)"))
              : ((J.style.display = ""), (q.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[te] = J.style.display === "none"));
          }));
      };
    (k("System Skills", p, !0),
      k("User Skills", h, !1),
      p.length === 0 &&
        h.length === 0 &&
        b.createEl("p", {
          text: `No skills found in ${a[l]}. Run setup to deploy skills.`,
          cls: "setting-item-description",
        }),
      this._advCollapsed === void 0 && (this._advCollapsed = !0));
    let g = r.createEl("div", { cls: "paperforge-collapsible-header" }),
      x = g.createEl("span", {
        text: "\u25B6",
        cls: "paperforge-collapsible-arrow",
      });
    x.style.transform = this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)";
    let C = g.createEl("span", {
        cls: "paperforge-collapsible-title",
        text: "Advanced",
      }),
      R = g.createEl("span", {
        cls: "paperforge-collapsible-sub",
        text: "Memory + Vector DB + Embedding",
      }),
      S = r.createEl("div", { cls: "paperforge-collapsible-content" });
    ((S.style.display = this._advCollapsed ? "none" : ""),
      g.addEventListener("click", () => {
        ((this._advCollapsed = !this._advCollapsed),
          (S.style.display = this._advCollapsed ? "none" : ""),
          (x.style.transform = this._advCollapsed
            ? "rotate(0deg)"
            : "rotate(90deg)"));
      }),
      S.createEl("h4", { text: "Memory Layer" }),
      S.createEl("div", { cls: "paperforge-desc-box" }).setText(
        f("feat_memory_desc")
      ));
    let B = S.createEl("div", { cls: "paperforge-memory-status" }),
      A = this.app.vault.adapter.basePath;
    (this.plugin._lastSyncTime &&
      !this._lastSyncTime &&
      (this._lastSyncTime = this.plugin._lastSyncTime),
      this._memoryStatusText === null && (this._memoryStatusText = Gt(A)),
      this._renderMemoryStatusText(
        B,
        this._memoryStatusText,
        this._lastSyncTime
      ),
      this._renderVectorSection(S));
  }
  _renderVectorSection(r) {
    var p;
    if (
      (r.createEl("h4", { text: "Vector Database" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      r
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(f("feat_vector_desc")),
      new z.Setting(r)
        .setName(f("feat_vector_enable"))
        .setDesc(f("feat_vector_enable_desc"))
        .addToggle((h) => {
          h.setValue(!!this.plugin.settings.features.vector_db).onChange(
            (b) => {
              ((this.plugin.settings.features.vector_db = b),
                this.plugin.saveSettings(),
                (this._vectorDepsOk = null),
                (this._embedStatusText = null),
                this.display());
            }
          );
        }),
      !this.plugin.settings.features.vector_db)
    )
      return;
    let i = this.app.vault.adapter.basePath,
      a = r.createEl("div", { cls: "paperforge-vec-header" }),
      c = a.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    a.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: f("feat_vector_config_label"),
    });
    let l = r.createEl("div", { cls: "paperforge-vector-config" }),
      u = (h) => {
        ((l.style.display = h ? "none" : ""),
          (c.style.transform = h ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (u(Dr(this._featurePanelsCollapsed, "vectorConfig", !1)),
      a.addEventListener("click", () => {
        let h = Bn(this._featurePanelsCollapsed, "vectorConfig", !1);
        u(h);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(l, i);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(l);
      return;
    }
    if (this._vectorDepsOk === null) {
      let h = Rt(i);
      ((this._vectorDepsOk = h && (p = h.deps_installed) != null ? p : !1),
        this._vectorDepsOk && (this._embedStatusText = gt(i)),
        this.display());
    }
  }
  _renderApiConfig(r) {
    (new z.Setting(r)
      .setName(f("feat_openai_key"))
      .setDesc(f("feat_openai_key_desc"))
      .addText((n) => {
        n.setPlaceholder("sk-...")
          .setValue(this.plugin.settings.vector_db_api_key || "")
          .onChange((i) => {
            ((this.plugin.settings.vector_db_api_key = i),
              this.plugin.saveSettings());
          });
      }),
      new z.Setting(r)
        .setName(f("feat_api_base_url"))
        .setDesc(f("feat_api_base_url_desc"))
        .addText((n) => {
          n.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((i) => {
              ((this.plugin.settings.vector_db_api_base = i),
                this.plugin.saveSettings());
            });
        }),
      new z.Setting(r)
        .setName(f("feat_api_model"))
        .setDesc(f("feat_api_model_desc"))
        .addText((n) => {
          n.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((i) => {
              ((this.plugin.settings.vector_db_api_model = i),
                this.plugin.saveSettings());
            });
        }));
  }
  _renderVectorNoDeps(r) {
    (r
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(f("feat_deps_missing")),
      new z.Setting(r)
        .setName(f("feat_install_deps"))
        .setDesc(f("feat_install_deps_desc"))
        .addButton((i) => {
          i.setButtonText(f("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let a = this.app.vault.adapter.basePath,
                c = Ue(a, this.plugin.settings);
              if (!c.path) {
                new z.Notice(f("feat_no_python"));
                return;
              }
              (i.setButtonText(f("feat_installing")), i.setDisabled(!0));
              let l = "chromadb openai",
                u = new z.Notice(
                  f("feat_installing_pkgs").replace("{pkgs}", l),
                  0
                );
              try {
                let p = Object.assign({}, process.env, {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  h = l.split(" ");
                (await new Promise((b, k) => {
                  (0, oe.execFile)(
                    c.path,
                    [...c.extraArgs, "-m", "pip", "install", ...h],
                    { cwd: a, timeout: 3e5, env: p, windowsHide: !0 },
                    (g) => {
                      g ? k(g) : b();
                    }
                  );
                }),
                  u.hide(),
                  new z.Notice(f("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = gt(a)),
                  this.display());
              } catch (p) {
                (u.hide(),
                  new z.Notice(
                    f("feat_install_failed") + (p.stderr || p.message || p)
                  ),
                  i.setButtonText(f("feat_retry_btn")),
                  i.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(r, n) {
    (r.createEl("div", { cls: "paperforge-desc-box" }).setText(gt(n)),
      this._renderApiConfig(r));
    let a = r.createEl("div", { cls: "paperforge-embed-section" });
    a.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: f("feat_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let l = a.createEl("div", { cls: "paperforge-embed-controls" }),
      u = a.createEl("div", { cls: "paperforge-embed-status-text" });
    (() => {
      var C, R, S;
      (l.empty(), u.empty());
      let h = (Rt(n) || {}).build_state || {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          h.status === "running" &&
          (this.plugin._embedProgress = {
            current: h.current || 0,
            total: h.total || 1,
            key: h.paper_id || "",
          }));
      let { current: b, total: k, key: g } = this.plugin._embedProgress;
      if (!!this.plugin._embedProcess || h.status === "running") {
        let F = l.createEl("div", { cls: "paperforge-progress-track" });
        F.style.cssText = "flex:1;";
        let B = k > 0 ? ((b / k) * 100).toFixed(1) : "0",
          A = F.createEl("div", { cls: "paperforge-progress-seg done" });
        if (
          ((A.style.cssText = `width:${B}%; min-width:${b > 0 ? "2px" : "0"};`),
          b < k)
        ) {
          let w = F.createEl("div", { cls: "paperforge-progress-seg pending" });
          w.style.cssText = `width:${(100 - parseFloat(B)).toFixed(1)}%;`;
        }
        (u.createEl("span", {
          cls: "paperforge-embed-progress-text",
          text: `${b}/${k} papers`,
        }),
          g &&
            u.createEl("span", {
              cls: "paperforge-embed-progress-key",
              text: ` (${g})`,
            }));
        let v = l.createEl("button");
        (v.setText("Stop"),
          (v.className = "mod-warning"),
          v.addEventListener("click", () => {
            (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
              this.plugin._embedProcess &&
                (this.plugin._embedProcess.kill(),
                (this.plugin._embedProcess = null)),
              this.display());
          }));
      } else {
        let F = Rt(n),
          B =
            ((C = F == null ? void 0 : F.chunk_count) != null ? C : 0) +
            ((R = F == null ? void 0 : F.body_chunk_count) != null ? R : 0) +
            ((S = F == null ? void 0 : F.object_chunk_count) != null ? S : 0),
          A = B > 0,
          v = F ? !!F.corrupted : !1,
          w = (M) => {
            if (!Ue(n, this.plugin.settings).path) {
              new z.Notice(f("feat_no_python"));
              return;
            }
            let J = Object.assign({}, process.env, {
              PYTHONIOENCODING: "utf-8",
              PYTHONUTF8: "1",
              VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || "",
              VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || "",
              VECTOR_DB_API_MODEL:
                this.plugin.settings.vector_db_api_model || "",
            });
            ((this.plugin._embedStderr = ""),
              (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
              (this.plugin._embedProcess = this._callPython(
                ["embed", "build", M],
                {
                  stream: !0,
                  env: J,
                  onData: (q) => {
                    let te = q.toString("utf-8").split(`
`);
                    for (let se of te)
                      if (se.startsWith("EMBED_START:"))
                        this.plugin._embedProgress.total =
                          parseInt(se.split(":")[1]) || 0;
                      else if (se.startsWith("EMBED_PROGRESS:")) {
                        let G = se.split(":");
                        ((this.plugin._embedProgress.current =
                          parseInt(G[1]) || 0),
                          (this.plugin._embedProgress.key = G[3] || ""));
                      } else
                        se.startsWith("EMBED_DONE") &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                    this.display();
                  },
                  onStderr: (q) => {
                    (this.plugin._embedStderr ||
                      (this.plugin._embedStderr = ""),
                      (this.plugin._embedStderr += q.toString("utf-8")));
                  },
                  onError: (q) => {
                    ((this.plugin._embedProcess = null),
                      new z.Notice(
                        f("feat_build_failed") + ": " + (q.message || q)
                      ),
                      this.display());
                  },
                  onClose: (q) => {
                    if (((this.plugin._embedProcess = null), q === 0))
                      ((this.plugin._embedProgress.current =
                        this.plugin._embedProgress.total),
                        this.plugin.saveSettings(),
                        (this._embedStatusText = gt(n)),
                        new z.Notice(f("feat_build_complete")));
                    else {
                      this._embedStatusText = null;
                      let te = (this.plugin._embedStderr || "").slice(0, 200);
                      new z.Notice(
                        f("feat_build_failed") + (te ? ": " + te : ""),
                        8e3
                      );
                    }
                    ((this.plugin._embedStderr = ""),
                      this.display(),
                      this._refreshSnapshots(n));
                  },
                }
              )),
              this.display());
          };
        if (v) {
          let M = a.createEl("div");
          ((M.style.cssText =
            "padding:8px 12px; margin:8px 0; background:var(--background-modifier-warning); border-radius:4px; font-size:12px; display:flex; align-items:center; justify-content:space-between;"),
            M.createEl("span", { text: f("feat_vector_corrupted") }));
          let I = M.createEl("button", {
            text: f("feat_vector_rebuild_force_btn"),
          });
          ((I.className = "mod-cta"),
            I.addEventListener("click", () => w("--force")));
        }
        A &&
          !v &&
          l.createEl("span", {
            text: B + " chunks embedded",
            cls: "setting-item-description",
          });
        let O = l.createEl("button");
        if (
          (O.setText(A ? f("feat_rebuild_btn") : f("feat_build_btn")),
          O.addClass("mod-cta"),
          O.addEventListener("click", () => w("--resume")),
          !v && A)
        ) {
          let M = l.createEl("button");
          (M.setText(f("feat_vector_rebuild_force_btn")),
            (M.style.marginLeft = "6px"),
            M.addEventListener("click", () => w("--force")));
        }
      }
    })();
  }
  _getCurrentModelKey() {
    return this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
  }
  _parseEmbedStatus(r) {
    let n = {};
    return (
      r &&
        (r
          .split(
            `
`
          )
          .forEach((i) => {
            let a = i.match(/^\s*([^:]+):\s*(.*)/);
            a && (n[a[1].trim()] = a[2].trim());
          }),
        n.db_exists !== void 0 && (n.db_exists = n.db_exists === "True"),
        n.chunk_count !== void 0 &&
          (n.chunk_count = parseInt(n.chunk_count, 10) || 0)),
      n
    );
  }
  _getPythonDesc(r, n) {
    return n === "stale"
      ? `[!!] ${r} (stale \u2014 path no longer exists, update or clear the override below)`
      : n === "manual"
        ? `${r} (manual)`
        : `${r} (auto-detected)`;
  }
  _refreshPythonInterpDesc(r, n) {
    let i = this._pythonInterpDescEl;
    i &&
      (n === "stale"
        ? (i.textContent = `[!!] ${r} (stale \u2014 path no longer exists, update or clear the override below)`)
        : n === "manual"
          ? (i.textContent = `${r} (manual)`)
          : (i.textContent = `${r} (auto-detected)`));
  }
  _validatePythonOverride() {
    let r = this.plugin.settings.python_path
        ? this.plugin.settings.python_path.trim()
        : "",
      n = this._customPathDescEl;
    if (!r) {
      let i = "\u8BF7\u8F93\u5165\u8DEF\u5F84 / Enter a path first";
      (n &&
        (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${i}</span>`),
        new z.Notice(i));
      return;
    }
    if (!ie.existsSync(r)) {
      let i = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (n &&
        (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${i}</span>`),
        new z.Notice(i, 4e3));
      return;
    }
    try {
      ie.accessSync(r, ie.constants.X_OK);
    } catch (i) {
      let a = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (n &&
        (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${a}</span>`),
        new z.Notice(a, 4e3));
      return;
    }
    (0, oe.execFile)(r, ["--version"], { timeout: 8e3 }, (i, a) => {
      if (i || !a) {
        let p = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (n &&
          (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${p}</span>`),
          new z.Notice(p, 4e3));
        return;
      }
      let c = a.match(/Python (\d+)\.(\d+)/);
      if (!c) {
        let p = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (n &&
          (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${p}</span>`),
          new z.Notice(p, 4e3));
        return;
      }
      let l = parseInt(c[1], 10),
        u = parseInt(c[2], 10);
      if (l < 3 || (l === 3 && u < 10)) {
        let p =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.10+ / Python version too low, need 3.10+";
        (n &&
          (n.innerHTML = `<span style="color:var(--text-error)">\u2717 ${p}</span>`),
          new z.Notice(p, 4e3));
        return;
      }
      (0, oe.execFile)(r, ["-m", "pip", "--version"], { timeout: 8e3 }, (p) => {
        if (p) {
          let h = `\u2713 Python ${l}.${u} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (n &&
            (n.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${h}</span>`),
            new z.Notice(h, 4e3));
        } else {
          let h = `\u2713 Python ${l}.${u} \u6709\u6548 / Valid`;
          (n &&
            (n.innerHTML = `<span style="color:var(--text-accent)">${h}</span>`),
            new z.Notice(h, 4e3));
        }
      });
    });
  }
  _syncRuntime(r) {
    let n = this.app.vault.adapter.basePath,
      { path: i, extraArgs: a = [] } = re(
        n,
        this.plugin.settings,
        void 0,
        void 0
      ),
      c = this.plugin.manifest.version,
      l = Fn(i, c, a);
    (r.setDisabled(!0), r.setButtonText(f("runtime_health_syncing")));
    let u = (h, b) => (
        console.log(`[PaperForge] Sync Runtime: trying ${b}`),
        Rn(l.cmd, h, n, l.timeout, void 0, ot())
      ),
      p = () => {
        let h = "opencode";
        try {
          let x = ie.readFileSync(me.join(n, "paperforge.json"), "utf-8"),
            C = JSON.parse(x);
          C.agent_key && (h = C.agent_key);
        } catch (x) {}
        let b = [
            ...a,
            "-c",
            'from paperforge.services.skill_deploy import deploy_skills; from pathlib import Path; r=deploy_skills(vault=Path(r"' +
              n.replace(/\\/g, "\\\\") +
              '"), agent_key="' +
              h +
              '", overwrite=True); print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
          ],
          k = (0, oe.spawn)(i, b, { cwd: n, timeout: 3e4, windowsHide: !0 }),
          g = "";
        (k.stdout.on("data", (x) => {
          g += x.toString("utf-8");
        }),
          k.on("close", (x) => {
            console.log(`[PaperForge] Skill deploy: ${g.trim()} (exit ${x})`);
          }));
      };
    u(l.pypiArgs, "PyPI").then((h) => {
      if (h.exitCode === 0) {
        (console.log("[PaperForge] Sync Runtime: installed via PyPI"),
          p(),
          new z.Notice(f("runtime_health_sync_done").replace("{0}", c), 5e3),
          this.display());
        return;
      }
      (console.warn(
        "[PaperForge] Sync Runtime: PyPI failed, falling back to git..."
      ),
        u(l.gitArgs, "git").then((b) => {
          b.exitCode === 0
            ? (console.log("[PaperForge] Sync Runtime: installed via git"),
              p(),
              new z.Notice(
                f("runtime_health_sync_done").replace("{0}", c),
                5e3
              ),
              this.display())
            : (r.setDisabled(!1),
              r.setButtonText(f("runtime_health_sync")),
              console.error("[PaperForge] git fallback stderr:", b.stderr),
              new z.Notice(
                f("runtime_health_sync_fail").replace(
                  "{0}",
                  "pip exit code " + b.exitCode
                ),
                8e3
              ));
        }));
    });
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _preCheck(r) {
    var c;
    let n = this.app.vault.adapter.basePath,
      { path: i, extraArgs: a = [] } = re(
        n,
        (c = this.plugin) == null ? void 0 : c.settings,
        void 0,
        void 0
      );
    (0, oe.execFile)(i, [...a, "--version"], { timeout: 8e3 }, (l, u) => {
      let p = [];
      p.push({
        label: "Python",
        ok: !l,
        detail: l ? f("check_python_fail") : u.trim(),
      });
      let h = !1,
        b = process.env.HOME || process.env.USERPROFILE || Vn.homedir() || "";
      if (process.platform === "darwin")
        h = [
          "/Applications/Zotero.app",
          me.join(b, "Applications", "Zotero.app"),
        ].some((F) => {
          try {
            return ie.existsSync(F);
          } catch (B) {
            return !1;
          }
        });
      else if (process.platform === "win32") {
        let S = process.env.ProgramFiles || "",
          F = process.env.LOCALAPPDATA || "";
        h = [
          me.join(S, "Zotero"),
          me.join(S, "(x86)", "Zotero"),
          me.join(F, "Programs", "Zotero"),
          me.join(F, "Zotero"),
          me.join(b, "AppData", "Local", "Programs", "Zotero"),
        ]
          .filter(Boolean)
          .some((A) => {
            try {
              return ie.existsSync(A);
            } catch (v) {
              return !1;
            }
          });
      } else
        h = [
          me.join(b, ".local", "share", "zotero", "zotero"),
          "/usr/bin/zotero",
          "/usr/local/bin/zotero",
        ].some((F) => {
          try {
            return ie.existsSync(F);
          } catch (B) {
            return !1;
          }
        });
      let k = this.plugin.settings.zotero_data_dir;
      if (!h && k)
        try {
          h = ie.existsSync(k);
        } catch (S) {}
      p.push({
        label: "Zotero",
        ok: h,
        detail: h ? f("check_zotero_ok") : f("check_zotero_fail"),
      });
      let g = !1,
        x = process.env.APPDATA || "";
      (process.platform === "win32" &&
        x &&
        (g = Jt(me.join(x, "Zotero", "Zotero", "Profiles"))),
        !g &&
          process.platform === "darwin" &&
          b &&
          (g = Jt(
            me.join(b, "Library", "Application Support", "Zotero", "Profiles")
          )),
        !g &&
          process.platform !== "win32" &&
          process.platform !== "darwin" &&
          b &&
          (g = Jt(me.join(b, ".zotero", "zotero", "Profiles"))),
        !g && k && String(k).trim() && (g = Fr(k.trim())),
        !g && b && (g = Fr(me.join(b, "Zotero"))),
        p.push({
          label: "Better BibTeX",
          ok: g,
          detail: g ? f("check_bbt_ok") : f("check_bbt_fail"),
        }));
      let C = { true: "\u2713", false: "\u2717" };
      if (this._checkEl) {
        this._checkEl.setText(
          p.map((F) => `${C[String(F.ok)]} ${F.label}: ${F.detail}`).join(`
`)
        );
        let S = p.some((F) => !F.ok);
        this._checkEl.className = `paperforge-message msg-${S ? "error" : "ok"}`;
      }
      let R = p.filter((S) => !S.ok);
      (R.length > 0 &&
        new z.Notice(
          `[!!] \u672A\u901A\u8FC7: ${R.map((S) => S.label).join(", ")}`,
          6e3
        ),
        r());
    });
  }
  _renderMaintenanceTab(r) {
    r.createEl("h2", { text: f("tab_maintenance") || "\u7EF4\u62A4" });
    let n = this.app.vault.adapter.basePath,
      i = r.createEl("div"),
      a = (k, g) =>
        g === "retry_ocr" || g === "upgrade_legacy"
          ? { cmd: ["-m", "paperforge", "ocr", "redo", ...k], timeout: 3e5 }
          : g === "rebuild_result"
            ? {
                cmd: ["-m", "paperforge", "ocr", "rebuild", ...k],
                timeout: 12e4,
              }
            : null,
      c = null;
    try {
      c = zn(n);
    } catch (k) {}
    let l = re(n, this.plugin.settings, ie, oe.execFileSync);
    if (!l.path) {
      i.createEl("p", {
        text: "\u26A0 Python \u672A\u914D\u7F6E\uFF0C\u8BF7\u5148\u5728\u300C\u5B89\u88C5\u300D\u6807\u7B7E\u9875\u914D\u7F6E\u3002",
        cls: "setting-item-description",
      });
      return;
    }
    let u = (k) => {
      i.empty();
      let g = k.filter((S) => S.visible_in_maintenance);
      if (g.length === 0) {
        i.createEl("p", {
          text: f("maintenance_all_good") || "\u2705 \u5168\u90E8\u6B63\u5E38",
        });
        return;
      }
      let x = l.path,
        C = l.extraArgs || [],
        R = [
          {
            key: "retry",
            title: f("maintenance_group_retry") || "\u9700\u8981\u91CD\u8BD5",
            items: [],
          },
          {
            key: "rebuild",
            title:
              f("maintenance_group_rebuild") ||
              "\u53EF\u91CD\u5EFA\u7ED3\u679C",
            items: [],
          },
          {
            key: "legacy_optional",
            title:
              f("maintenance_group_legacy") ||
              "\u53EF\u5347\u7EA7\u65E7\u7ED3\u679C\uFF08\u53EF\u9009\uFF09",
            items: [],
          },
        ];
      for (let S of g) {
        let F = R.find((B) => B.key === S.display_group);
        F && F.items.push(S);
      }
      for (let S of R) {
        if (S.items.length === 0) continue;
        let F = S.key === "legacy_optional",
          B = F ? i.createEl("details") : i.createEl("div");
        F
          ? B.createEl("summary").createEl("strong", {
              text: S.title + " (" + S.items.length + ")",
            })
          : B.createEl("h3", { text: S.title + " (" + S.items.length + ")" });
        let A = new Map();
        for (let V of S.items) A.set(V.key, !1);
        let v = B.createEl("div", { cls: "pf-maint-toolbar" }),
          w = v.createEl("button", { text: "\u5168\u9009" }),
          O = v.createEl("button", { text: "\u53D6\u6D88\u5168\u9009" }),
          M = v.createEl("button", {
            text: "\u25B6 \u6267\u884C\u5DF2\u9009",
            cls: "mod-cta",
          }),
          I = v.createEl("span", { cls: "pf-maint-exec-label" }),
          J = () => {
            let V = S.items.filter((U) => A.get(U.key)).length;
            I.setText("\u5DF2\u9009 " + V + " \u7BC7");
          };
        (J(),
          w.addEventListener("click", () => {
            for (let U of S.items) A.set(U.key, !0);
            (J(),
              B.querySelectorAll("input[type=checkbox].pf-maint-sel").forEach(
                (U) => {
                  U.checked = !0;
                }
              ));
          }),
          O.addEventListener("click", () => {
            for (let U of S.items) A.set(U.key, !1);
            (J(),
              B.querySelectorAll("input[type=checkbox].pf-maint-sel").forEach(
                (U) => {
                  U.checked = !1;
                }
              ));
          }),
          M.addEventListener("click", () => {
            let V = S.items.filter((U) => A.get(U.key));
            if (V.length === 0) {
              new z.Notice(
                "\u8BF7\u5148\u9009\u62E9\u8981\u5904\u7406\u7684\u8BBA\u6587\u3002"
              );
              return;
            }
            for (let U of V) {
              let be = a([U.key], U.display_action);
              be &&
                (0, oe.execFile)(
                  x,
                  [...C, ...be.cmd],
                  { cwd: n, timeout: be.timeout, windowsHide: !0 },
                  () => {
                    new z.Notice(U.display_label + " \u2014 " + U.key);
                  }
                );
            }
          }));
        let te = B.createEl("div", { cls: "pf-maint-table-wrap" }).createEl(
            "table",
            { cls: "pf-maint-table" }
          ),
          se = te.createEl("thead"),
          G = te.createEl("tbody"),
          ye = se.insertRow();
        [
          "",
          "Key",
          "Title",
          "\u5EFA\u8BAE\u64CD\u4F5C",
          "\u539F\u56E0",
          "\u64CD\u4F5C",
        ].forEach((V) => {
          let U = document.createElement("th");
          ((U.textContent = V), ye.appendChild(U));
        });
        let ue = (V) =>
          V === "retry_ocr"
            ? f("maintenance_btn_retry") || "\u91CD\u8BD5"
            : V === "rebuild_result"
              ? f("maintenance_btn_rebuild") || "\u91CD\u5EFA"
              : V === "upgrade_legacy"
                ? f("maintenance_btn_upgrade") || "\u5347\u7EA7"
                : "";
        for (let V of S.items) {
          let U = G.insertRow(),
            be = U.insertCell();
          be.style.cssText = "padding:3px 4px;text-align:center;";
          let we = document.createElement("input");
          ((we.type = "checkbox"),
            (we.className = "pf-maint-sel"),
            (we.checked = A.get(V.key) || !1),
            we.addEventListener("change", () => {
              (A.set(V.key, we.checked), J());
            }),
            be.appendChild(we));
          let ge = U.insertCell();
          ((ge.style.cssText =
            "padding:3px 4px;white-space:nowrap;font-size:11px;max-width:90px;overflow:hidden;text-overflow:ellipsis;"),
            (ge.textContent = V.key));
          let Ce = U.insertCell();
          ((Ce.style.cssText =
            "padding:3px 4px;white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis;"),
            (Ce.textContent = V.title || V.key));
          let fe = U.insertCell();
          ((fe.style.cssText = "padding:3px 4px;white-space:nowrap;"),
            (fe.textContent = V.display_label));
          let Le = U.insertCell();
          ((Le.style.cssText =
            "padding:3px 4px;white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis;font-size:11px;color:var(--text-muted);"),
            (Le.textContent = V.display_reason || ""));
          let De = U.insertCell();
          De.style.cssText =
            "padding:3px 4px;text-align:center;white-space:nowrap;";
          let Ie = document.createElement("button");
          ((Ie.textContent = ue(V.display_action)),
            Ie.textContent &&
              (Ie.addEventListener("click", () => {
                let K = a([V.key], V.display_action);
                K &&
                  (0, oe.execFile)(
                    x,
                    [...C, ...K.cmd],
                    { cwd: n, timeout: K.timeout, windowsHide: !0 },
                    () => {
                      new z.Notice(V.display_label + " \u2014 " + V.key);
                    }
                  );
              }),
              De.appendChild(Ie)));
        }
      }
    };
    if (c) {
      let k = Object.values(c.papers);
      u(k);
    } else
      i.createEl("p", {
        text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026",
      });
    ($n(n, l.path, l.extraArgs || [], c || null)
      .then((k) => {
        k.changed
          ? (u(k.data),
            Yt(n, {
              manifest: {},
              papers: Object.fromEntries(k.data.map((g) => [g.key, g])),
              cached_at: new Date().toISOString(),
            }))
          : c ||
            (u(k.data),
            Yt(n, {
              manifest: {},
              papers: Object.fromEntries(k.data.map((g) => [g.key, g])),
              cached_at: new Date().toISOString(),
            }));
      })
      .catch(() => {
        c ||
          (i.empty(),
          i.createEl("p", {
            text: "\u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002",
            cls: "setting-item-description",
          }));
      }),
      r.createEl("hr"),
      r.createEl("h3", { text: "\u5168\u5C40\u64CD\u4F5C" }));
    let p = r.createEl("div", { cls: "pf-maint-global" });
    (p
      .createEl("button", { text: "\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15" })
      .addEventListener("click", () => {
        (new z.Notice("\u6B63\u5728\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15\u2026"),
          (0, oe.execFile)(
            l.path,
            [
              ...(l.extraArgs || []),
              "-m",
              "paperforge",
              "embed",
              "build",
              "--force",
            ],
            { cwd: n, timeout: 3e5, windowsHide: !0 },
            () => {
              new z.Notice(
                "\u641C\u7D22\u7D22\u5F15\u91CD\u5EFA\u5B8C\u6210\u3002"
              );
            }
          ));
      }),
      p
        .createEl("button", { text: "\u91CD\u5EFA\u8BB0\u5FC6\u5E93" })
        .addEventListener("click", () => {
          (new z.Notice("\u6B63\u5728\u91CD\u5EFA\u8BB0\u5FC6\u5E93\u2026"),
            (0, oe.execFile)(
              l.path,
              [...(l.extraArgs || []), "-m", "paperforge", "repair", "--fix"],
              { cwd: n, timeout: 12e4, windowsHide: !0 },
              () => {
                new z.Notice(
                  "\u8BB0\u5FC6\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002"
                );
              }
            ));
        }));
  }
  _renderReleaseNotesTab(r) {
    (r.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      r.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let n = qn.default.versions || [];
    for (let c of n) {
      let l = r.createEl("div", { cls: "paperforge-release-card" }),
        u = l.createEl("div", { cls: "paperforge-release-header" });
      if (
        (u.createEl("strong", { text: `v${c.version} \u2014 ${c.title}` }),
        u.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${c.date})`,
        }),
        c.breaking_or_migration && c.breaking_or_migration.length > 0)
      ) {
        let p = l.createEl("div", { cls: "paperforge-release-section" });
        p.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let h of c.breaking_or_migration)
          p.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${h}`,
          });
      }
      if (c.new_features && c.new_features.length > 0) {
        let p = l.createEl("div", { cls: "paperforge-release-section" });
        p.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let h of c.new_features)
          p.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${h}`,
          });
      }
      if (c.fixes && c.fixes.length > 0) {
        let p = l.createEl("div", { cls: "paperforge-release-section" });
        p.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let h of c.fixes)
          p.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${h}`,
          });
      }
      if (c.recommended_actions && c.recommended_actions.length > 0) {
        let p = l.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        p.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let h of c.recommended_actions)
          p.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${h}`,
          });
      }
    }
    (r.createEl("h3", { text: "\u4F7F\u7528\u624B\u518C" }),
      r
        .createEl("div", { cls: "paperforge-manual-links" })
        .createEl("a", {
          text: "\u2192 \u67E5\u770B\u5B8C\u6574\u4F7F\u7528\u624B\u518C\uFF08GitHub\uFF09",
          href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
        })
        .setAttr("target", "_blank"));
  }
};
var X = require("obsidian"),
  We = ae(require("fs")),
  Mt = ae(require("path")),
  et = require("child_process");
var At = ae(require("path"));
function Hn(_) {
  if (!_) return null;
  let y = At.dirname(_);
  for (;;) {
    let r = At.basename(y);
    if (!r || r === ".") break;
    let n = r.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (n) return n[1];
    let i = At.dirname(y);
    if (i === y) break;
    y = i;
  }
  return null;
}
var pe = ae(require("fs")),
  Ye = ae(require("path"));
function Bt(_) {
  return Te(_).ocrDir;
}
function Ys(_, y) {
  let r = Ye.join(Bt(_), y, "versions", "manifest.json");
  try {
    if (!pe.existsSync(r)) return null;
    let n = pe.readFileSync(r, "utf-8"),
      i = JSON.parse(n);
    if (i && typeof i == "object" && "versions" in i && "current" in i) {
      let a = i,
        c = a.versions,
        l = a.current;
      if (Array.isArray(c) && l && typeof l == "object" && "label" in l)
        return i;
    }
    return null;
  } catch (n) {
    return null;
  }
}
function ea(_) {
  let y = Bt(_);
  try {
    return pe.existsSync(y)
      ? pe
          .readdirSync(y, { withFileTypes: !0 })
          .filter((r) => r.isDirectory())
          .map((r) => r.name)
      : [];
  } catch (r) {
    return [];
  }
}
function Br(_) {
  let y = ea(_),
    r = [];
  for (let n of y) {
    let i = Ys(_, n);
    if (!i) continue;
    let a = i.versions.map((l) => l.label),
      c = 0;
    for (let l of a) {
      let u = Ye.join(Bt(_), n, "versions", l, "fulltext.md");
      try {
        pe.existsSync(u) && (c += pe.statSync(u).size);
      } catch (p) {}
    }
    r.push({
      key: n,
      title: n.replace(/_/g, " "),
      versions: i.versions,
      currentLabel: i.current.label,
      totalSize: c,
    });
  }
  return (r.sort((n, i) => n.title.localeCompare(i.title)), r);
}
function Un(_, y, r) {
  let n = Bt(_),
    i = Ye.join(n, y, "versions", r, "fulltext.md"),
    a = Ye.join(n, y, "render"),
    c = Ye.join(a, "fulltext.md");
  try {
    return pe.existsSync(i)
      ? (pe.existsSync(a) || pe.mkdirSync(a, { recursive: !0 }),
        pe.copyFileSync(i, c),
        !0)
      : !1;
  } catch (l) {
    return !1;
  }
}
function Wn(_, y, r, n) {
  var g;
  let i = Bt(_),
    a = Ye.join(i, y, "versions", r, "fulltext.md"),
    c = Ye.join(i, y, "versions", n, "fulltext.md"),
    l = "",
    u = "";
  try {
    pe.existsSync(a) && (l = pe.readFileSync(a, "utf-8"));
  } catch (x) {}
  try {
    pe.existsSync(c) && (u = pe.readFileSync(c, "utf-8"));
  } catch (x) {}
  let p = Kn(l),
    h = Kn(u),
    b = Math.max(p.length, h.length),
    k = [];
  for (let x = 0; x < b; x++) {
    let C = x < p.length ? p[x] : "",
      R = x < h.length ? h[x] : "",
      S =
        (g = (C || R).split(`
`)[0]) != null
          ? g
          : "",
      F = S.startsWith("## ") ? S.replace(/^##\s+/, "") : "",
      B = "unchanged";
    (!C && R
      ? (B = "added")
      : C && !R
        ? (B = "removed")
        : C !== R && (B = "changed"),
      B !== "unchanged" &&
        k.push({
          paragraphIndex: x,
          heading: F,
          type: B,
          oldText: C || void 0,
          newText: R || void 0,
        }));
  }
  return k;
}
function Kn(_) {
  let y = _.split(`
`),
    r = [],
    n = [];
  for (let i of y)
    if (i.startsWith("## ") && n.length > 0)
      (r.push(
        n
          .join(
            `
`
          )
          .trim()
      ),
        (n = [i]));
    else if (i.trim() === "" && n.length > 0) {
      let a = n
        .join(
          `
`
        )
        .trim();
      a && (r.push(a), (n = []));
    } else n.push(i);
  if (n.length > 0) {
    let i = n
      .join(
        `
`
      )
      .trim();
    i && r.push(i);
  }
  return r;
}
var sr = ae(require("fs")),
  Or = ae(require("path")),
  Jn = ae(Zn()),
  Mr = null,
  mt = null;
function ta(_) {
  if (((_ = _.trim()), !_)) return "";
  if (_.startsWith('"') && _.endsWith('"')) return _;
  let y = _.split(/\s+/).filter(Boolean);
  return y.length === 0 ? "" : y.join(" AND ");
}
function ct(_) {
  return _ == null
    ? ""
    : typeof _ == "string"
      ? _
      : _ instanceof Uint8Array
        ? new TextDecoder().decode(_)
        : String(_);
}
function ra(_) {
  return _ == null ? 0 : typeof _ == "number" ? _ : Number(_);
}
async function Gn(_) {
  let y = Or.join(_, "System", "PaperForge", "indexes", "paperforge.db");
  if (!sr.existsSync(y))
    throw new Error(`PaperForge database not found at ${y}`);
  let r = await (0, Jn.default)({ locateFile: (i) => Or.join(__dirname, i) }),
    n = sr.readFileSync(y);
  ((Mr = new r.Database(new Uint8Array(n))),
    (mt =
      Mr.prepare(`SELECT zotero_key, title, first_author, year, journal, domain, abstract, rank
     FROM paper_fts
     WHERE paper_fts MATCH ?
     ORDER BY rank
     LIMIT ?`)));
}
function Qn(_, y = 20) {
  if (!Mr || !mt) return null;
  let r = ta(_);
  if (!r) return [];
  mt.bind([r, y]);
  let n = [];
  for (; mt.step(); ) {
    let i = mt.getAsObject();
    n.push({
      zotero_key: ct(i.zotero_key),
      title: ct(i.title),
      first_author: ct(i.first_author),
      year: ct(i.year),
      journal: ct(i.journal),
      domain: ct(i.domain),
      abstract: ct(i.abstract),
      rank: ra(i.rank),
    });
  }
  return (mt.reset(), n);
}
var yt = class extends X.ItemView {
  constructor(r) {
    super(r);
    this._currentMode = null;
    this._currentDomain = null;
    this._currentPaperKey = null;
    this._currentPaperEntry = null;
    this._currentFilePath = null;
    this._cachedItems = null;
    this._modeSubscribers = [];
    this._leafChangeTimer = null;
    this._ocrPrivacyShown = !1;
    this._cachedStats = null;
    this._techDetailsExpanded = !1;
    this._paperforgeVersion = "";
    this._dashboardPermissions = {};
    this._headerTitle = null;
    this._versionBadge = null;
    this._messageEl = null;
    this._metricsEl = null;
    this._ocrSection = null;
    this._ocrEmpty = null;
    this._ocrBadge = null;
    this._ocrTrack = null;
    this._ocrCounts = null;
    this._driftBannerEl = null;
    this._versionPapers = null;
    this._versionFilter = "";
    this._searchContainer = null;
    this._searchInput = null;
    this._searchResultsEl = null;
    this._searchTimer = void 0;
    this._sqlJsInitialized = !1;
    this._sqlJsFailed = !1;
    ((this._currentMode = null),
      (this._currentDomain = null),
      (this._currentPaperKey = null),
      (this._currentPaperEntry = null),
      (this._currentFilePath = null),
      (this._cachedItems = null),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      (this._ocrPrivacyShown = !1));
  }
  getViewType() {
    return it;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Ct;
  }
  async onOpen() {
    (this._buildPanel(),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      this._setupEventSubscriptions(),
      this._fetchVersion(),
      this._detectAndSwitch());
  }
  async onClose() {
    if (this._modeSubscribers && this._modeSubscribers.length > 0) {
      for (let r of this._modeSubscribers)
        r.event === "active-leaf-change"
          ? this.app.workspace.off("active-leaf-change", r.ref)
          : r.event === "modify" && this.app.vault.off("modify", r.ref);
      this._modeSubscribers = [];
    }
    (this._leafChangeTimer &&
      (clearTimeout(this._leafChangeTimer), (this._leafChangeTimer = null)),
      (this._cachedItems = null),
      (this._cachedStats = null));
  }
  _buildPanel() {
    let r = this.containerEl;
    (r.empty(), r.addClass("paperforge-status-panel"));
    let n = r.createEl("div", { cls: "paperforge-header" }),
      i = n.createEl("div", { cls: "paperforge-header-left" });
    (i.createEl("div", { cls: "paperforge-header-logo", text: "P" }),
      (this._modeContextEl = i.createEl("div", {
        cls: "paperforge-mode-context",
      })),
      (this._headerTitle = i.createEl("h3", {
        cls: "paperforge-header-title",
        text: "PaperForge",
      })),
      (this._versionBadge = i.createEl("span", {
        cls: "paperforge-header-badge",
        text: "v\u2014",
      })));
    let a = n.createEl("button", {
      cls: "paperforge-header-refresh",
      attr: { "aria-label": "Refresh" },
    });
    ((a.innerHTML = "\u21BB"),
      a.addEventListener("click", () => {
        (this._invalidateIndex(), this._detectAndSwitch());
      }),
      (this._messageEl = r.createEl("div", { cls: "paperforge-message" })),
      (this._contentEl = r.createEl("div", {
        cls: "paperforge-content-area",
      })));
  }
  _fetchVersion() {
    var l, u;
    let r = this.app.vault.adapter.basePath,
      n = this.app.plugins.plugins.paperforge,
      i =
        ((l = n == null ? void 0 : n.manifest) == null ? void 0 : l.version) ||
        "?",
      { path: a, extraArgs: c = [] } = re(
        r,
        (u = n == null ? void 0 : n.settings) != null ? u : null,
        void 0,
        void 0
      );
    Cn(a, i, r, 1e4, void 0).then((p) => {
      if (p.status === "not-installed") return;
      let h = p.pyVersion || "";
      ((this._paperforgeVersion = h.startsWith("v") ? h : "v" + h),
        this._versionBadge &&
          this._versionBadge.setText(this._paperforgeVersion),
        this._driftBannerEl &&
        i &&
        this._paperforgeVersion !== "v" + i.replace(/^v/, "")
          ? ((this._driftBannerEl.style.display = "block"),
            this._driftBannerEl.setText(
              f("dashboard_drift_warning")
                .replace("{0}", this._paperforgeVersion)
                .replace("{1}", "v" + i.replace(/^v/, ""))
            ))
          : this._driftBannerEl &&
            (this._driftBannerEl.style.display = "none"));
    });
  }
  _fetchStats(r) {
    var l;
    if (!this._metricsEl) return;
    if (!r && !this._cachedStats)
      (this._metricsEl.empty(),
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "Loading...",
        }));
    else if (r && !this._cachedStats) return;
    let n = this.app.vault.adapter.basePath,
      i = this.app.plugins.plugins.paperforge,
      { path: a, extraArgs: c = [] } = re(
        n,
        (l = i == null ? void 0 : i.settings) != null ? l : null,
        void 0,
        void 0
      );
    (0, et.execFile)(
      a,
      [...c, "-m", "paperforge", "dashboard", "--json"],
      { cwd: n, timeout: 3e4 },
      (u, p) => {
        if (!u)
          try {
            let h = JSON.parse(p);
            if (h.ok && h.data) {
              let b = this._normalizeDashboardData(h.data);
              ((this._cachedStats = b),
                this._metricsEl.empty(),
                this._renderStats(b),
                this._renderOcr(b),
                (this._dashboardPermissions = h.data.permissions || {}));
              return;
            }
          } catch (h) {}
        this._fallbackFetchStats(r, n, i);
      }
    );
  }
  _normalizeDashboardData(r) {
    let n = r.stats || {},
      i = n.ocr_health || {},
      a = n.pdf_health || {},
      c = r.ocr_version_state || {},
      l = (i.done || 0) + (i.pending || 0) + (i.failed || 0);
    return {
      total_papers: n.papers || 0,
      formal_notes: n.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: l,
        pending: i.pending || 0,
        processing: 0,
        done: i.done || 0,
        failed: i.failed || 0,
      },
      path_errors: (a.broken || 0) + (a.missing || 0),
      ocr_version_state: {
        total_papers: c.total_papers || 0,
        derived_stale_count: c.derived_stale_count || 0,
        raw_upgradable_count: c.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(r, n, i) {
    var l, u, p;
    let a =
        ((l = i == null ? void 0 : i.settings) == null
          ? void 0
          : l.system_dir) || "System",
      c = Mt.join(n, a, "PaperForge", "indexes", "formal-library.json");
    try {
      let h = We.readFileSync(c, "utf-8"),
        b = JSON.parse(h),
        k = b.items || [],
        g = {},
        x = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        C = 0,
        R = 0,
        S = 0,
        F = 0,
        B = 0,
        A = 0;
      for (let v of k) {
        v.note_path && A++;
        let w = v.lifecycle || "pdf_ready";
        g[w] = (g[w] || 0) + 1;
        let O = v.health || {};
        for (let I of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (O[I] || "healthy") === "healthy" ? x[I].healthy++ : x[I].unhealthy++;
        let M = v.ocr_status || "";
        (C++,
          M === "done"
            ? R++
            : M === "pending"
              ? S++
              : M === "processing" || M === "queued" || M === "running"
                ? F++
                : B++);
      }
      ((this._cachedStats = {
        version:
          b.paperforge_version ||
          ((u = this._cachedStats) == null ? void 0 : u.version) ||
          "\u2014",
        total_papers: k.length,
        formal_notes: A,
        exports: 0,
        bases: 0,
        ocr: { total: C, pending: S, processing: F, done: R, failed: B },
        path_errors: 0,
        lifecycle_level_counts: g,
        health_aggregate: x,
      }),
        this._metricsEl.empty(),
        this._renderStats(this._cachedStats),
        this._renderOcr(this._cachedStats));
    } catch (h) {
      !r &&
        !this._cachedStats &&
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "No index \u2014 trying CLI...",
        });
      let { path: b, extraArgs: k = [] } = re(
        n,
        (p = i == null ? void 0 : i.settings) != null ? p : null,
        void 0,
        void 0
      );
      (0, et.execFile)(
        b,
        [...k, "-m", "paperforge", "status", "--json"],
        { cwd: n, timeout: 3e4 },
        (g, x) => {
          if (g) {
            if (this._cachedStats) return;
            this._metricsEl.createEl("div", {
              cls: "paperforge-status-error",
              text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
            });
            return;
          }
          try {
            let C = JSON.parse(x);
            ((this._cachedStats = C),
              this._metricsEl.empty(),
              this._renderStats(C),
              this._renderOcr(C));
          } catch (C) {
            this._cachedStats ||
              this._metricsEl.createEl("div", {
                cls: "paperforge-status-error",
                text: "Invalid response from paperforge status.",
              });
          }
        }
      );
    }
  }
  _renderSkeleton(r) {
    r.addClass("paperforge-loading");
  }
  _renderEmptyState(r, n) {
    r.createEl("div", { cls: "paperforge-empty-state", text: n || "No data" });
  }
  _buildMetricBar(r, n, i) {
    if (i <= 0) return;
    let a = Math.min(100, (n / i) * 100);
    r.createEl("div", { cls: "paperforge-metric-progress" }).createEl("div", {
      cls: "paperforge-metric-progress-fill",
      attr: { style: `width:${a.toFixed(1)}%` },
    });
  }
  _loadIndex() {
    var c;
    let r = this.app.vault.adapter.basePath,
      n = this.app.plugins.plugins.paperforge,
      i =
        ((c = n == null ? void 0 : n.settings) == null
          ? void 0
          : c.system_dir) || "System",
      a = Mt.join(r, i, "PaperForge", "indexes", "formal-library.json");
    try {
      let l = We.readFileSync(a, "utf-8");
      return JSON.parse(l);
    } catch (l) {
      return null;
    }
  }
  _getCachedIndex() {
    if (!this._cachedItems) {
      let r = this._loadIndex();
      this._cachedItems = r ? r.items || [] : [];
    }
    return this._cachedItems;
  }
  _findEntry(r) {
    if (!r) return null;
    let n = this._getCachedIndex().find((i) => i.zotero_key === r) || null;
    return wn(this.app, n);
  }
  _patchCachedEntry(r, n) {
    if (!r || !this._cachedItems) return;
    let i = this._cachedItems.findIndex((a) => a.zotero_key === r);
    i !== -1 && (this._cachedItems[i] = xr(this._cachedItems[i], n));
  }
  _filterByDomain(r) {
    return r ? this._getCachedIndex().filter((n) => n.domain === r) : [];
  }
  _renderStats(r) {
    var l;
    if (
      (this._versionBadge &&
        this._versionBadge.setText(
          this._paperforgeVersion || (r.version ? "v" + r.version : "v\u2014")
        ),
      !r || typeof r.total_papers == "undefined")
    ) {
      this._metricsEl && this._renderSkeleton(this._metricsEl);
      return;
    }
    if (!this._metricsEl) return;
    this._metricsEl.removeClass("paperforge-loading");
    let n = r.total_papers || 0,
      i = r.formal_notes || 0,
      a = [
        { value: n, label: "Papers", color: "var(--color-cyan)", barMax: 0 },
        {
          value: i,
          label: "Formal Notes",
          color: "var(--color-blue)",
          barMax: n,
        },
        {
          value: r.exports || 0,
          label: "Exports",
          color: "var(--color-purple)",
          barMax: 0,
        },
      ];
    for (let u of a) {
      let p = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (p.style.setProperty("--metric-color", u.color),
        p.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((l = u.value) == null ? void 0 : l.toString()) || "\u2014",
        }),
        p.createEl("div", { cls: "paperforge-metric-label", text: u.label }),
        u.barMax > 0 && this._buildMetricBar(p, u.value, u.barMax));
    }
    let c = r.ocr_version_state || {};
    if (
      c.total_papers > 0 &&
      (c.derived_stale_count > 0 || c.raw_upgradable_count > 0)
    ) {
      let u = [];
      (c.derived_stale_count > 0 && u.push(`${c.derived_stale_count} stale`),
        c.raw_upgradable_count > 0 &&
          u.push(`${c.raw_upgradable_count} upgradable`));
      let p = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (p.style.setProperty("--metric-color", "var(--color-yellow)"),
        p.createEl("div", {
          cls: "paperforge-metric-value",
          text: u.join(", "),
        }),
        p.createEl("div", {
          cls: "paperforge-metric-label",
          text: "OCR Version",
        }));
    }
  }
  _renderOcr(r) {
    if (!this._ocrSection) return;
    let n = r.ocr || {},
      i = n.total || 0;
    if (i === 0) {
      this._ocrSection.style.display = "none";
      return;
    }
    ((this._ocrSection.style.display = "block"),
      this._ocrEmpty && (this._ocrEmpty.style.display = "none"));
    let a = n.done || 0,
      c = n.pending || 0,
      l = n.processing || 0,
      u = n.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        l > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : c > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        l > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let p = [
        { cls: "pending", count: c },
        { cls: "active", count: l },
        { cls: "done", count: a },
        { cls: "failed", count: u },
      ];
      for (let h of p)
        if (h.count > 0) {
          let b = ((h.count / i) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${h.cls}`,
            attr: { style: `width:${b}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let p = [
        { cls: "pending", value: c, label: "Pending" },
        { cls: "active", value: l, label: "Processing" },
        { cls: "done", value: a, label: "Done" },
        { cls: "failed", value: u, label: "Failed" },
      ];
      for (let h of p) {
        let b = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (b.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: h.value.toString(),
        }),
          b.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: h.label,
          }));
      }
    }
  }
  _renderLifecycleStepper(r, n, i) {
    if (!n || !i) {
      this._renderSkeleton(r);
      return;
    }
    let a = [
        { key: "indexed", label: "Indexed" },
        { key: "pdf_ready", label: "PDF Ready" },
        { key: "fulltext_ready", label: "Fulltext Ready" },
        { key: "deep_read_done", label: "Deep Read" },
      ],
      c = r.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      l = !1;
    for (let u of a) {
      let p = c.createEl("div", { cls: "step" });
      (p.createEl("div", { cls: "step-indicator" }),
        p.createEl("div", { cls: "step-label", text: u.label }),
        u.key === i
          ? (p.addClass("current"), (l = !0))
          : l
            ? p.addClass("pending")
            : p.addClass("completed"));
    }
  }
  _renderHealthMatrix(r, n) {
    if (!n) {
      this._renderSkeleton(r);
      return;
    }
    let i = [
        {
          key: "pdf_health",
          label: "PDF Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "ocr_health",
          label: "OCR Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "note_health",
          label: "Note Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "asset_health",
          label: "Asset Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
      ],
      a = r.createEl("div", { cls: "paperforge-health-matrix" });
    for (let c of i) {
      let l = n[c.key] || "healthy",
        u = a.createEl("div", { cls: "paperforge-health-cell" }),
        p,
        h,
        b;
      (l === "healthy" || l === "ok"
        ? ((p = c.iconOk), (h = "ok"), (b = `${c.label}: OK`))
        : l === "warn" || l === "warning" || l === "degraded"
          ? ((p = c.iconWarn),
            (h = "warn"),
            (b = `${c.label}: Needs Attention`))
          : ((p = c.iconFail), (h = "fail"), (b = `${c.label}: Failed`)),
        u.addClass(h),
        u.setAttribute("title", b),
        u.createEl("div", { cls: "paperforge-health-cell-icon", text: p }),
        u.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: c.label,
        }));
    }
  }
  _renderMaturityGauge(r, n, i) {
    if (n == null || n === void 0) {
      this._renderSkeleton(r);
      return;
    }
    let a = r.createEl("div", { cls: "paperforge-maturity-gauge" }),
      c = a.createEl("div", { cls: "gauge-track" }),
      l = 4,
      u = Math.max(1, Math.min(l, Math.round(n)));
    for (let p = 1; p <= l; p++) {
      let h = c.createEl("div", { cls: "gauge-segment" });
      p <= u && (h.addClass("filled"), h.addClass(`level-${p}`));
    }
    if (
      (a.createEl("div", { cls: "gauge-level", text: `Level ${u} / ${l}` }),
      u < l && i)
    ) {
      let p = typeof i == "string" ? [i] : i;
      if (p.length > 0) {
        let h = a.createEl("ul", { cls: "gauge-blockers" });
        for (let b of p) h.createEl("li", { text: b });
      }
    }
  }
  _renderBarChart(r, n) {
    if (!n || Object.keys(n).length === 0) {
      this._renderEmptyState(r, "No lifecycle data");
      return;
    }
    let i = [
        { key: "indexed", label: "Indexed", cls: "stage-indexed" },
        { key: "pdf_ready", label: "PDF Ready", cls: "stage-pdf-ready" },
        {
          key: "fulltext_ready",
          label: "Fulltext Ready",
          cls: "stage-fulltext-ready",
        },
        { key: "deep_read_done", label: "Deep Read", cls: "stage-deep-read" },
      ],
      a = r.createEl("div", { cls: "paperforge-bar-chart" }),
      c = Math.max(1, ...i.map((l) => n[l.key] || 0));
    for (let l of i) {
      let u = n[l.key] || 0,
        p = (u / c) * 100,
        h = a.createEl("div", { cls: "bar-row" });
      (h.createEl("div", { cls: "bar-label", text: l.label }),
        h
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${l.cls}`,
            attr: { style: `width:${p.toFixed(1)}%` },
          }),
        h.createEl("div", { cls: "bar-count", text: u.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(r) {
    return Hn(r);
  }
  _resolveModeForFile(r) {
    if (!r) return { mode: "global", filePath: null, key: null, domain: null };
    let n = r.extension,
      i = r.path;
    if (n === "base")
      return {
        mode: "collection",
        filePath: i,
        key: null,
        domain: r.basename.trim(),
      };
    if (n === "md") {
      let c = this.app.metadataCache.getFileCache(r),
        l = c && c.frontmatter && c.frontmatter.zotero_key;
      if (l) return { mode: "paper", filePath: i, key: l, domain: null };
    }
    if (n === "pdf") {
      let c = this._getCachedIndex();
      for (let l of c) {
        let u = (l.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((u ? u[1] : l.pdf_path) === i)
          return {
            mode: "paper",
            filePath: i,
            key: l.zotero_key,
            domain: null,
          };
      }
    }
    let a = this._extractZoteroKeyFromPath(i);
    return a
      ? { mode: "paper", filePath: i, key: a, domain: null }
      : { mode: "global", filePath: i, key: null, domain: null };
  }
  _detectAndSwitch() {
    let r = this._resolveModeForFile(this.app.workspace.getActiveFile());
    ((this._currentDomain = r.domain || null),
      (this._currentPaperKey = r.key || null),
      (this._currentPaperEntry = r.key ? this._findEntry(r.key) : null),
      this._switchMode(r.mode, r.filePath));
  }
  _switchMode(r, n) {
    if (this._currentMode === r && this._currentFilePath === n) {
      this._refreshCurrentMode();
      return;
    }
    if (
      ((this._currentMode = r),
      (this._currentFilePath = n),
      (this._techDetailsExpanded = !1),
      !!this._contentEl)
    )
      switch (
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader(r),
        r)
      ) {
        case "global":
          this._renderGlobalMode();
          break;
        case "paper":
          this._renderPaperMode();
          break;
        case "collection":
          this._renderCollectionMode();
          break;
        case "versions":
          this._renderVersionMode();
          break;
      }
  }
  _renderGlobalMode() {
    var we, ge, Ce, fe, Le, De, Ie;
    if (!this._contentEl) return;
    let r = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = r.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let n = this._getCachedIndex(),
      i = n.length,
      a = 0,
      c = 0,
      l = 0;
    for (let K of n)
      (K.has_pdf && a++,
        K.ocr_status === "done" && c++,
        K.deep_reading_status === "done" && l++);
    let u = r.createEl("div", { cls: "paperforge-library-snapshot" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let p = u.createEl("div", { cls: "paperforge-snapshot-pills" }),
      h = [
        { value: i, label: "papers" },
        { value: a, label: "PDFs ready" },
        { value: c, label: "OCR done" },
        { value: l, label: "deep-read done" },
      ];
    for (let K of h) {
      let j = p.createEl("div", { cls: "paperforge-snapshot-pill" });
      (j.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(K.value),
      }),
        j.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + K.label,
        }));
    }
    let b = r.createEl("div", { cls: "paperforge-system-status" });
    b.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let k = b.createEl("div", { cls: "paperforge-status-grid" }),
      g = this.app.plugins.plugins.paperforge,
      x =
        ((we = g == null ? void 0 : g.manifest) == null
          ? void 0
          : we.version) || "?",
      C = this._paperforgeVersion;
    if (!C)
      try {
        let K = this.app.vault.adapter.basePath,
          { path: j, extraArgs: ke = [] } = re(
            K,
            (ge = g == null ? void 0 : g.settings) != null ? ge : null,
            void 0,
            void 0
          ),
          ce = (0, et.execFileSync)(
            j,
            [...ke, "-c", "import paperforge; print(paperforge.__version__)"],
            { cwd: K, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
          ).trim();
        ce &&
          ((C = ce.startsWith("v") ? ce : "v" + ce),
          (this._paperforgeVersion = C));
      } catch (K) {}
    C = C || "\u2014";
    let R = C === "v" + x;
    this._renderSystemStatusRow(
      k,
      "Runtime",
      R ? "healthy" : "mismatch",
      R ? "v" + x : "plugin v" + x + " \u2260 CLI " + C
    );
    let S = this._loadIndex(),
      F = S && S.items && S.items.length > 0;
    this._renderSystemStatusRow(
      k,
      "Index",
      F ? "healthy" : "missing",
      F ? S.items.length + " entries" : "formal-library.json not found"
    );
    let B =
        ((Ce = g == null ? void 0 : g.settings) == null
          ? void 0
          : Ce.system_dir) || "System",
      A = this.app.vault.adapter.basePath,
      v = !1,
      w = "No exports found";
    try {
      let K = Mt.join(A, B, "PaperForge", "exports");
      if (We.existsSync(K)) {
        let j = We.readdirSync(K).filter((ke) => ke.endsWith(".json"));
        ((v = j.length > 0),
          (w = v ? j.length + " export(s)" : "No JSON exports"));
      }
    } catch (K) {}
    this._renderSystemStatusRow(
      k,
      "Zotero Export",
      v ? "healthy" : "missing",
      w
    );
    let O = !!(
      (fe = g == null ? void 0 : g.settings) != null && fe.paddleocr_api_key
    );
    if (!O)
      try {
        let K =
            ((Le = g == null ? void 0 : g.settings) == null
              ? void 0
              : Le.system_dir) || "System",
          j = Mt.join(A, K, "PaperForge", ".env");
        if (We.existsSync(j)) {
          let ce = We.readFileSync(j, "utf-8").match(
            /^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m
          );
          O = !!(ce && ce[1] && ce[1].trim());
        }
      } catch (K) {}
    (O ||
      (O = !!(
        process.env.PADDLEOCR_API_TOKEN ||
        process.env.PADDLEOCR_API_KEY ||
        process.env.OCR_TOKEN
      )),
      this._renderSystemStatusRow(
        k,
        "OCR Token",
        O ? "configured" : "missing",
        O ? "Configured" : "Not set"
      ));
    let M = !1,
      I = "",
      J = this.app.vault.adapter.basePath,
      q = Tr(J);
    ((M = An(J)),
      (I =
        (q && ((De = q.summary) == null ? void 0 : De.reason)) ||
        (q && ((Ie = q.summary) == null ? void 0 : Ie.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        k,
        "Memory Layer",
        M ? "healthy" : "fail",
        I
      ));
    let te = !R && C !== "\u2014";
    if (te || !F || !v || !O) {
      let K = r.createEl("div", { cls: "paperforge-issue-summary" });
      K.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let j = K.createEl("div", { cls: "paperforge-issue-list" });
      (te &&
        j.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        F ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        v ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        O ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let ke = K.createEl("div", { cls: "paperforge-issue-actions" }),
        ce = ke.createEl("button", { cls: "paperforge-contextual-btn" });
      (ce.createEl("span", { text: "Run Doctor" }),
        ce.addEventListener("click", () => {
          let Ne = Pe.find((vt) => vt.id === "paperforge-doctor");
          Ne && this._runAction(Ne, ce);
        }));
      let Ae = ke.createEl("button", { cls: "paperforge-contextual-btn" });
      (Ae.createEl("span", { text: "Repair Issues" }),
        Ae.addEventListener("click", () => {
          let Ne = Pe.find((vt) => vt.id === "paperforge-repair");
          Ne && this._runAction(Ne, Ae);
        }));
    }
    let G = r.createEl("div", { cls: "paperforge-global-actions" });
    G.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let ye = G.createEl("div", { cls: "paperforge-global-actions-row" }),
      ue = ye.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (ue.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      ue.createEl("span", { text: "Open Literature Hub" }),
      ue.addEventListener("click", () => {
        var ke;
        let K =
            ((ke = g == null ? void 0 : g.settings) == null
              ? void 0
              : ke.base_dir) || "Bases",
          j = this.app.vault.getAbstractFileByPath(K);
        if (j) {
          let ce = null;
          if (
            (j.children &&
              (ce = j.children.find((Ae) => Ae.extension === "base")),
            ce)
          ) {
            let Ae = this.app.workspace.getLeaf(!1);
            Ae && Ae.openFile(ce);
          } else new X.Notice("[!!] No .base file found in " + K, 6e3);
        } else new X.Notice("[!!] Base directory not found: " + K, 6e3);
      }));
    let V = ye.createEl("button", { cls: "paperforge-contextual-btn" });
    (V.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      V.createEl("span", { text: "Sync Library" }),
      V.addEventListener("click", () => {
        let K = Pe.find((j) => j.id === "paperforge-sync");
        K && this._runAction(K, V);
      }));
    let U = ye.createEl("button", { cls: "paperforge-contextual-btn" });
    (U.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      U.createEl("span", { text: "Run OCR" }),
      U.addEventListener("click", () => {
        let K = Pe.find((j) => j.id === "paperforge-ocr");
        K && this._runAction(K, U);
      }));
    let be = ye.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (be.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      be.createEl("span", { text: "Redo OCR" }),
      be.addEventListener("click", () => {
        let K = Pe.find((j) => j.id === "paperforge-ocr-redo");
        K && this._runAction(K, be);
      }));
  }
  _renderSystemStatusRow(r, n, i, a) {
    let c = r.createEl("div", { cls: "paperforge-status-row" });
    (c
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(i === "healthy" || i === "configured" ? "ok" : "fail"),
      c.createEl("span", { cls: "paperforge-status-label", text: n }),
      c.createEl("span", { cls: "paperforge-status-detail", text: a || "" }));
  }
  _renderPaperMode() {
    let r = this._currentPaperEntry,
      n = this._currentPaperKey;
    if (!this._contentEl) return;
    if (!n) {
      this._renderEmptyState(this._contentEl, "No paper data available.");
      return;
    }
    if (!r) {
      this._contentEl.createEl("div", {
        cls: "paperforge-content-placeholder",
        text: 'Paper "' + n + '" not found in canonical index. Sync first.',
      });
      return;
    }
    let i = this._contentEl.createEl("div", { cls: "paperforge-paper-view" }),
      a = i.createEl("div", { cls: "paperforge-paper-header" });
    a.createEl("div", {
      cls: "paperforge-paper-title pf-copy",
      text: r.title || "Untitled",
    }).addEventListener("click", () => {
      (navigator.clipboard.writeText(r.title || ""),
        new X.Notice("Title copied"));
    });
    let l = a.createEl("div", { cls: "paperforge-paper-meta" });
    (r.authors &&
      r.authors.length > 0 &&
      l.createEl("span", {
        cls: "paperforge-paper-authors",
        text: r.authors.join(", "),
      }),
      r.year &&
        l.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(r.year),
        }));
    let u = i.createEl("div", { cls: "paperforge-status-strip" }),
      p = u.createEl("div", { cls: "paperforge-status-strip-left" }),
      h = u.createEl("div", { cls: "paperforge-status-strip-right" }),
      b = [
        { key: "pdf", label: "PDF", ok: r.has_pdf === !0 },
        {
          key: "ocr",
          label: "OCR",
          ok: r.ocr_status === "done",
          pending: ["pending", "queued", "processing"].includes(
            r.ocr_status || ""
          ),
          fail: ["failed", "blocked", "done_incomplete", "nopdf"].includes(
            r.ocr_status || ""
          ),
        },
        {
          key: "deep",
          label: "\u7CBE\u8BFB",
          ok: r.deep_reading_status === "done",
        },
      ];
    for (let g of b) {
      let x = p.createEl("span", { cls: "paperforge-status-pill" }),
        C = "pending";
      (g.ok ? (C = "ok") : g.fail ? (C = "fail") : g.pending && (C = "pending"),
        x.addClass(C));
      let R = g.ok ? "\u2713" : g.fail ? "\u2717" : "\u25CB";
      (x.createEl("span", { cls: "paperforge-status-pill-icon", text: R }),
        x.createEl("span", { text: " " + g.label }));
    }
    if (r.pdf_path) {
      let g = h.createEl("button", { cls: "paperforge-contextual-btn" });
      (g.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        g.createEl("span", { text: "\u6253\u5F00 PDF" }),
        g.addEventListener("click", () => {
          let x = r.pdf_path.match(/\[\[([^\]]+)\]\]/),
            C = x ? x[1] : r.pdf_path;
          this.app.vault.getAbstractFileByPath(C)
            ? this.app.workspace.openLinkText(C, "")
            : new X.Notice("[!!] PDF not found: " + C, 6e3);
        }));
    }
    if (r.fulltext_path) {
      let g = h.createEl("button", { cls: "paperforge-contextual-btn" });
      (g.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        g.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        g.addEventListener("click", () => this._openFulltext(r.fulltext_path)));
    }
    let k = h.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (k.createEl("span", { text: f("version_panel_title") }),
      k.addEventListener("click", () => {
        this._switchToVersionMode(n);
      }),
      this._renderPaperOverviewCard(i, r),
      r.next_step === "ready" && r.deep_reading_status === "done")
    ) {
      let g = i.createEl("div", { cls: "paperforge-complete-row" });
      (g.createEl("span", { text: "\u2713" }),
        g.createEl("span", {
          text: "\u5DF2\u5B8C\u6210\uFF0C\u53EF\u76F4\u63A5\u4F7F\u7528",
        }));
    } else this._renderNextStepCard(i, r, n);
    (this._renderRecentDiscussionCard(i, r),
      this._renderPaperTechnicalDetails(i, r));
  }
  _renderPaperOverviewCard(r, n) {
    let i = r.createEl("div", { cls: "paperforge-paper-overview" });
    i.createEl("div", { cls: "paperforge-paper-overview-header" }).createEl(
      "span",
      {
        cls: "paperforge-paper-overview-title",
        text: "\u6587\u7AE0\u6982\u89C8",
      }
    );
    let c = i.createEl("div", { cls: "paperforge-paper-overview-body" }),
      l = c.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (n.note_path) {
      let u = this.app.vault.getAbstractFileByPath(n.note_path);
      u
        ? this.app.vault
            .read(u)
            .then((p) => {
              let h = this._extractOverviewFromNote(p);
              if (h) {
                let b = h.length > 200 ? h.slice(0, 200) + "..." : h;
                if ((l.setText(b), h.length > 200)) {
                  let k = c.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    g = k.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  g.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let x = !1;
                  k.addEventListener("click", () => {
                    (l.setText(x ? b : h),
                      (g.innerHTML = x
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (x = !x));
                  });
                }
              } else
                l.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              l.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : l.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else l.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
  }
  _extractOverviewFromNote(r) {
    if (!r) return null;
    let n = r.indexOf("## \u{1F50D} \u7CBE\u8BFB");
    if (n === -1) return null;
    let i = r.slice(n),
      a = [
        "**\u4E00\u53E5\u8BDD\u603B\u89C8:**",
        "**\u4E00\u53E5\u8BDD\u603B\u89C8**",
        "**\u6587\u7AE0\u6458\u8981:**",
        "**\u6587\u7AE0\u6458\u8981**",
      ];
    for (let u of a) {
      let p = i.indexOf(u);
      if (p !== -1) {
        let h = i.slice(p + u.length),
          b = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          k = h.length;
        for (let C of b) {
          let R = h.indexOf(C);
          R !== -1 && R < k && (k = R);
        }
        let g = h.indexOf(`

`);
        g !== -1 && g < k && (k = g);
        let x = h.slice(0, k).trim();
        return (
          x.startsWith("**") && (x = x.slice(2)),
          x.endsWith("**") && (x = x.slice(0, -2)),
          x || null
        );
      }
    }
    let c = i.indexOf(`
`);
    if (c === -1) return null;
    let l = i
      .slice(c + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !l || l.startsWith("###") || l.startsWith("##")
      ? null
      : l.length > 300
        ? l.slice(0, 300) + "..."
        : l;
  }
  _renderRecentDiscussionCard(r, n) {
    let i = r.createEl("div", { cls: "paperforge-discussion-card" });
    if (((i.style.display = "none"), !n.note_path)) return;
    let a = n.note_path.lastIndexOf("/"),
      l = (a !== -1 ? n.note_path.substring(0, a) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(l)
      .then((u) => {
        if (u) return this.app.vault.adapter.read(l);
      })
      .then(async (u) => {
        if (!u) return;
        let p = this._parseDiscussionMD(u);
        if (!p || p.length === 0) return;
        ((i.style.display = "block"),
          i
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let k of p) {
          let g = i.createEl("div", { cls: "paperforge-discussion-item" }),
            x = g.createEl("div", { cls: "paperforge-discussion-q" });
          (x.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            x.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: k.question,
            }));
          let C = g.createEl("div", { cls: "paperforge-discussion-a" }),
            R = !1;
          if (
            (k.answer &&
              k.answer.length > 500 &&
              ((R = !0), C.classList.add("paperforge-discussion-a-collapsed")),
            await X.MarkdownRenderer.render(
              this.app,
              k.answer || "",
              C,
              l,
              this
            ),
            R)
          ) {
            let S = !1;
            ((g.style.cursor = "pointer"),
              g.addEventListener("click", () => {
                ((S = !S),
                  C.classList.toggle("paperforge-discussion-a-collapsed", !S),
                  C.classList.toggle("paperforge-discussion-a-expanded", S));
              }));
          }
        }
        i.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (k) => {
          (k.preventDefault(),
            this.app.vault.getAbstractFileByPath(l)
              ? this.app.workspace.openLinkText(l, "")
              : new X.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((u) => {
        console.error("PaperForge: discussion.md read error", l, u.message);
      });
  }
  _parseDiscussionMD(r) {
    let n = r.split(/\n## /).slice(1);
    if (n.length === 0) return null;
    let i = n[n.length - 1],
      a = [],
      c = i.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let l of c) {
      let u = l.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!u) continue;
      let p = l.substring(0, u.index).trim(),
        h = l.substring(u.index + 3 + 4).trim();
      a.push({ question: p, answer: h });
    }
    return a.slice(-3);
  }
  _renderPaperTechnicalDetails(r, n) {
    let i = this._currentPaperKey,
      a = r.createEl("div", { cls: "paperforge-technical-details" }),
      c = a.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      l = a.createEl("div", { cls: "paperforge-technical-details-body" });
    ((l.style.display = "none"),
      this._techDetailsExpanded
        ? ((l.style.display = "block"),
          c.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : c.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      c.addEventListener("click", () => {
        let g = l.style.display !== "none";
        ((l.style.display = g ? "none" : "block"),
          c.setText(
            g
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !g));
      }));
    let u = l.createEl("div", { cls: "paperforge-workflow-toggles" }),
      p = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let g of p) {
      let x = u.createEl("label", { cls: "paperforge-workflow-toggle" }),
        C = x.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((C.checked = n[g.key] === !0),
        x.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: g.label,
        }),
        x.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: g.hint,
        }),
        C.addEventListener("change", async () => {
          let R = n.note_path
            ? this.app.vault.getAbstractFileByPath(n.note_path)
            : null;
          if (!R) {
            new X.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let S = C.checked;
          (await this.app.fileManager.processFrontMatter(R, (F) => {
            F[g.key] = S;
          }),
            this._patchCachedEntry(i, { [g.key]: S }),
            (this._currentPaperEntry = xr(this._currentPaperEntry, {
              [g.key]: S,
            })));
        }));
    }
    let h = n.health || {},
      b = [
        ["PDF Health", h.pdf_health || "\u2014"],
        ["OCR Status", n.ocr_status || "\u2014"],
        ["Asset Health", h.asset_health || "\u2014"],
        ["Note Path", n.note_path || "\u2014"],
        ["Fulltext Path", n.fulltext_path || "\u2014"],
      ],
      k = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [g, x] of b) {
      let C = l.createEl("div", { cls: "paperforge-technical-row" });
      C.createEl("span", { cls: "paperforge-technical-label", text: g });
      let R = C.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(x),
      });
      k.has(g) &&
        x &&
        x !== "\u2014" &&
        (R.addClass("pf-copy"),
        R.addEventListener("click", () => {
          (navigator.clipboard.writeText(x), new X.Notice(g + " copied"));
        }));
    }
  }
  _renderNextStepCard(r, n, i) {
    var p, h;
    let a = n.next_step || "ready",
      c = {
        sync: {
          label: "Sync Needed",
          text: "This paper needs to be synced from Zotero. Click to run sync.",
          cmd: "sync",
          icon: "\u21BB",
        },
        ocr: {
          label: "OCR Needed",
          text: "Fulltext is missing but PDF is present. Click to run OCR.",
          cmd: "ocr",
          icon: "\u229E",
        },
        repair: {
          label: "Repair Needed",
          text: "State divergence or path errors detected. Click to repair.",
          cmd: "repair",
          icon: "\u21BA",
        },
        "rebuild index": {
          label: "Rebuild Needed",
          text: "Index may be stale. Click to run sync to rebuild.",
          cmd: "sync",
          icon: "\u21BB",
        },
        "/pf-deep": {
          label: "Ready for Deep Reading",
          text: "Fulltext is ready. Copy /pf-deep command and run in your agent.",
          cmd: null,
          icon: "\u{1F50D}",
        },
        ready: {
          label: "All Set",
          text: "This paper is fully processed and ready for use.",
          cmd: "ready",
          icon: "\u2713",
        },
      },
      l = c[a] || c.ready,
      u = r.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (a === "ready" && u.addClass("ready"),
      u.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      u.createEl("div", { cls: "paperforge-next-step-text", text: l.text }),
      l.cmd && l.cmd !== "ready")
    ) {
      let b = u.createEl("button", { cls: "paperforge-next-step-trigger" });
      (b.createEl("span", { text: l.icon + "  " + l.label }),
        b.addEventListener("click", () => {
          let k = Pe.find((g) => g.cmd === l.cmd);
          k && this._runAction(k, b);
        }));
    } else if (a === "/pf-deep") {
      let b = u.createEl("button", { cls: "paperforge-next-step-trigger" });
      (b.createEl("span", { text: "\u{1F4CB}  " + f("copy_pf_deep_cmd") }),
        b.addEventListener("click", () => {
          let R = "/pf-deep " + i;
          navigator.clipboard
            .writeText(R)
            .then(() => {
              (b.setText("\u2713  " + f("copied")),
                new X.Notice(R + " copied"));
            })
            .catch(() => {
              new X.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let k =
          ((h =
            (p = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : p.settings) == null
            ? void 0
            : h.agent_platform) || "opencode",
        x =
          {
            opencode: "OpenCode",
            claude: "Claude Code",
            cursor: "Cursor",
            github_copilot: "GitHub Copilot",
            windsurf: "Windsurf",
            codex: "Codex",
            gemini: "Gemini CLI",
            cline: "Cline",
          }[k] || k;
      u.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        f("run_in_agent").replace("{0}", x)
      );
    } else
      a === "ready" &&
        u
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + l.label });
  }
  _openFulltext(r) {
    if (!r) {
      new X.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let n = this.app.vault.getAbstractFileByPath(r);
    n
      ? this.app.workspace.openLinkText(n.path, "")
      : new X.Notice("[!!] Fulltext file not found: " + r, 6e3);
  }
  _renderCollectionMode() {
    let r = this._currentDomain || "Unknown",
      n = this._filterByDomain(r);
    if (n.length === 0) {
      this._renderGlobalMode();
      return;
    }
    if (!this._contentEl) return;
    let i = this._contentEl.createEl("div", {
        cls: "paperforge-collection-view",
      }),
      a = n.length,
      c = 0,
      l = 0,
      u = 0,
      p = 0,
      h = 0,
      b = 0,
      k = 0;
    for (let v of n) {
      (v.has_pdf && c++,
        v.ocr_status === "done" && l++,
        v.ocr_status === "done" && v.analyze === !0 && u++,
        v.deep_reading_status === "done" && p++);
      let w = v.ocr_status || "";
      w === "pending" || w === "queued"
        ? h++
        : w === "processing"
          ? b++
          : (w === "failed" ||
              w === "blocked" ||
              w === "done_incomplete" ||
              w === "nopdf") &&
            k++;
    }
    i.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: r,
    });
    let x = i.createEl("div", { cls: "paperforge-workflow-overview" });
    x.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let C = x.createEl("div", { cls: "paperforge-workflow-funnel" }),
      R = [
        { value: a, label: "Total" },
        { value: c, label: "PDF Ready" },
        { value: l, label: "OCR Done" },
        { value: p, label: "Deep Read" },
      ];
    for (let v = 0; v < R.length; v++) {
      let w = C.createEl("div", { cls: "paperforge-workflow-stage" });
      (w.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(R[v].value),
      }),
        w.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: R[v].label,
        }),
        v < R.length - 1 &&
          C.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (h + b + l + k > 0) {
      let v = i.createEl("div", { cls: "paperforge-ocr-section" }),
        w = v.createEl("div", { cls: "paperforge-collection-ocr-header" });
      w.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let O = w.createEl("span", { cls: "paperforge-ocr-badge idle" });
      b > 0
        ? (O.addClass("active"), O.setText("Processing"))
        : h > 0
          ? O.setText("Pending")
          : (O.addClass("idle"), O.setText("Idle"));
      let M = v.createEl("div", { cls: "paperforge-progress-track" });
      b > 0 && M.addClass("paperforge-processing");
      let I = h + b + l + k,
        J = [
          { cls: "pending", count: h },
          { cls: "active", count: b },
          { cls: "done", count: l },
          { cls: "failed", count: k },
        ];
      for (let se of J)
        if (se.count > 0) {
          let G = ((se.count / I) * 100).toFixed(1);
          M.createEl("div", {
            cls: `paperforge-progress-seg ${se.cls}`,
            attr: { style: `width:${G}%` },
          });
        }
      let q = v.createEl("div", { cls: "paperforge-ocr-counts" }),
        te = [
          { cls: "pending", value: h, label: "Pending" },
          { cls: "active", value: b, label: "Processing" },
          { cls: "done", value: l, label: "Done" },
          { cls: "failed", value: k, label: "Attention" },
        ];
      for (let se of te) {
        let G = q.createEl("div", { cls: "paperforge-ocr-count" });
        (G.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: se.value.toString(),
        }),
          G.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: se.label,
          }));
      }
    }
    let S = i.createEl("div", { cls: "paperforge-collection-actions" }),
      F = S.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (F.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      F.createEl("span", { text: "Run OCR" }),
      F.addEventListener("click", () => {
        let v = Pe.find((w) => w.id === "paperforge-ocr");
        v && this._runAction(v, F);
      }));
    let B = S.createEl("button", { cls: "paperforge-contextual-btn" });
    (B.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      B.createEl("span", { text: "Sync Library" }),
      B.addEventListener("click", () => {
        let v = Pe.find((w) => w.id === "paperforge-sync");
        v && this._runAction(v, B);
      }));
    let A = S.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (A.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      A.createEl("span", { text: "Redo OCR" }),
      A.addEventListener("click", () => {
        let v = Pe.find((w) => w.id === "paperforge-ocr-redo");
        v && this._runAction(v, A);
      }),
      this.renderSearchSection(i));
  }
  _refreshCurrentMode() {
    if (!(!this._currentMode || !this._contentEl)) {
      (this._contentEl.empty(),
        this._contentEl.addClass("switching"),
        this._invalidateIndex(),
        (this._currentPaperEntry = this._currentPaperKey
          ? this._findEntry(this._currentPaperKey)
          : null),
        this._renderModeHeader(this._currentMode));
      try {
        switch (this._currentMode) {
          case "global":
            this._renderGlobalMode();
            break;
          case "paper":
            this._renderPaperMode();
            break;
          case "collection":
            this._renderCollectionMode();
            break;
          case "versions":
            this._renderVersionMode();
            break;
        }
      } finally {
        setTimeout(() => {
          this._contentEl && this._contentEl.removeClass("switching");
        }, 50);
      }
    }
  }
  _switchToVersionMode(r) {
    let i = this.app.vault.adapter.basePath,
      a = typeof i == "string" ? i : "";
    if (!a) {
      new X.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = Br(a)),
      (this._versionFilter = ""),
      (this._currentMode = "versions"),
      (this._currentFilePath = null),
      (this._techDetailsExpanded = !1),
      this._contentEl &&
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader("versions"),
        this._renderVersionMode()));
  }
  _renderVersionMode() {
    if (!this._contentEl) return;
    let r = this._contentEl.createEl("div", {
        cls: "paperforge-version-panel",
      }),
      i = this.app.vault.adapter.basePath,
      a = typeof i == "string" ? i : "";
    if (!a) {
      r.createEl("div", {
        cls: "paperforge-status-error",
        text: "Could not determine vault path",
      });
      return;
    }
    (!this._versionPapers || this._versionPapers.length === 0) &&
      (this._versionPapers = Br(a));
    let c = r.createEl("div", { cls: "paperforge-version-left" }),
      l = r.createEl("div", { cls: "paperforge-version-right" }),
      u = c.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: f("version_filter_placeholder") },
      });
    u.value = this._versionFilter;
    let p = c.createEl("div", { cls: "paperforge-version-paper-list" }),
      h = () => {
        p.empty();
        let F = this._versionFilter.toLowerCase(),
          B = this._versionPapers
            ? this._versionPapers.filter(
                (v) =>
                  !F ||
                  v.key.toLowerCase().includes(F) ||
                  v.title.toLowerCase().includes(F)
              )
            : [];
        if (B.length === 0) {
          p.createEl("div", {
            cls: "paperforge-meta",
            text: f("version_no_backups"),
          });
          return;
        }
        let A = p.createEl("div", {
          cls: "paperforge-meta",
          text: f("version_papers_count").replace("{n}", String(B.length)),
        });
        for (let v of B) {
          let w = p.createEl("div", { cls: "paperforge-version-paper-item" }),
            O = w.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: v.title,
            }),
            M = w.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: v.versions.map((I) => I.label).join(" "),
            });
          w.addEventListener("click", () => {
            (p
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((I) => I.removeClass("selected")),
              w.addClass("selected"),
              k(v));
          });
        }
      };
    u.addEventListener("input", () => {
      ((this._versionFilter = u.value), h());
    });
    let b = l.createEl("div", { cls: "paperforge-version-timeline-area" }),
      k = (F) => {
        if (
          (b.empty(),
          b
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: F.title }),
          F.versions.length === 0)
        ) {
          b.createEl("div", {
            cls: "paperforge-meta",
            text: f("version_no_backups"),
          });
          return;
        }
        let A = b.createEl("div", { cls: "paperforge-version-timeline" });
        for (let v of F.versions) {
          let w = v.label === F.currentLabel,
            O = A.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (w ? " paperforge-version-current" : ""),
            }),
            M = O.createEl("div", { cls: "paperforge-version-dot" }),
            I = O.createEl("div", { cls: "paperforge-version-content" }),
            J = I.createEl("div", { cls: "paperforge-version-label-row" });
          (J.createEl("span", {
            cls: "paperforge-version-label",
            text: v.label,
          }),
            w &&
              J.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: f("version_current"),
              }));
          let q = v.created_at ? v.created_at.slice(0, 10) : "";
          I.createEl("div", {
            cls: "paperforge-meta",
            text: q + " \u2014 " + v.source,
          });
          let te = v.fulltext_size
            ? v.fulltext_size > 1024
              ? (v.fulltext_size / 1024).toFixed(0) + "KB"
              : v.fulltext_size + "B"
            : "";
          te && I.createEl("div", { cls: "paperforge-meta", text: te });
          let se = I.createEl("div", { cls: "paperforge-version-actions" });
          (se
            .createEl("button", {
              cls: "pf-btn-primary",
              text: f("version_restore_btn"),
            })
            .addEventListener("click", () => {
              Un(a, F.key, v.label)
                ? new X.Notice(
                    f("version_restore_done").replace("{label}", v.label)
                  )
                : new X.Notice("Restore failed", 6e3);
            }),
            F.versions.length > 1 &&
              !w &&
              se
                .createEl("button", {
                  cls: "pf-btn-secondary",
                  text: f("version_compare_btn"),
                })
                .addEventListener("click", () => {
                  x(F, v.label, F.currentLabel);
                }));
        }
      },
      g = l.createEl("div", { cls: "paperforge-version-compare" });
    g.style.display = "none";
    let x = (F, B, A) => {
        let v = Wn(a, F.key, B, A);
        ((g.style.display = "block"), g.empty());
        let w = g.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (w.createEl("span", {
            cls: "pf-title",
            text: f("version_compare_title")
              .replace("{vA}", B)
              .replace("{vB}", A),
          }),
          w.createEl("span", {
            cls: "paperforge-meta",
            text: f("version_compare_paragraphs").replace(
              "{n}",
              String(v.length)
            ),
          }),
          v.length === 0)
        ) {
          g.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let O = g.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let M of v) {
          let I = O.createEl("div", { cls: "paperforge-version-diff-row" }),
            J =
              M.type === "added" ? "[+]" : M.type === "removed" ? "[-]" : "[~]",
            q = M.heading || "paragraph " + (M.paragraphIndex + 1);
          (I.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: J + " " + q,
          }),
            M.oldText &&
              I.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: M.oldText.slice(0, 200),
              }),
            M.newText &&
              I.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: M.newText.slice(0, 200),
              }));
        }
      },
      C = r.createEl("div", { cls: "paperforge-version-actions-bar" }),
      R = C.createEl("button", {
        cls: "pf-btn-primary",
        text: f("version_restore_selected"),
      }),
      S = C.createEl("button", {
        cls: "pf-btn-secondary",
        text: f("version_clear_old").replace("{size}", ""),
      });
    h();
  }
  renderSearchSection(r) {
    ((this._searchContainer = r.createEl("div", {
      cls: "paperforge-search-section",
    })),
      this._searchContainer
        .createEl("div", { cls: "paperforge-search-header" })
        .createEl("span", { cls: "pf-label", text: "Search" }));
    let i = this._searchContainer.createEl("div", {
        cls: "paperforge-search-input-row",
      }),
      a = i.createEl("span", { cls: "paperforge-search-mode", text: "M" });
    ((this._searchInput = i.createEl("input", {
      cls: "paperforge-search-input",
      attr: {
        type: "text",
        placeholder: "Search papers... (@ for deep search)",
      },
    })),
      (this._searchResultsEl = this._searchContainer.createEl("div", {
        cls: "paperforge-search-results",
      })),
      this._searchInput.addEventListener("input", () => {
        var l;
        let c = ((l = this._searchInput) == null ? void 0 : l.value) || "";
        (c.startsWith("@") && !c.startsWith("@ ")
          ? (a.setText("@"), a.addClass("deep"))
          : (a.setText("M"), a.removeClass("deep")),
          clearTimeout(this._searchTimer),
          !c.startsWith("@") &&
            c.trim() &&
            (this._searchTimer = setTimeout(() => {
              this.executeSearch({ source: "sqljs" });
            }, 200)));
      }),
      this._searchInput.addEventListener("keydown", (c) => {
        c.key === "Enter" &&
          (c.preventDefault(),
          this._searchTimer &&
            (clearTimeout(this._searchTimer), (this._searchTimer = void 0)),
          this.executeSearch({ source: "cli" }));
      }));
  }
  async executeSearch(r = {}) {
    if (!this._searchInput || !this._searchResultsEl) return;
    let n = this._searchInput.value.trim();
    if (!n) return;
    let i = n.startsWith("@"),
      a = i ? n.slice(1).trim() : n;
    if (!a) return;
    let c = i ? "retrieve" : "search",
      l = this.app.vault.adapter,
      u = "";
    if (l && typeof l == "object" && "basePath" in l) {
      let R = l.basePath;
      u = typeof R == "string" ? R : "";
    }
    if (
      (this._searchResultsEl.empty(),
      c === "search" && (r.source === "auto" || r.source === "sqljs") && u)
    )
      try {
        if (
          (!this._sqlJsInitialized &&
            !this._sqlJsFailed &&
            (await Gn(u), (this._sqlJsInitialized = !0)),
          this._sqlJsInitialized)
        ) {
          let R = Qn(a, 20);
          if (R !== null) {
            this.renderSearchResults(R, !1);
            return;
          }
        }
      } catch (R) {
        (console.error("PaperForge sql.js search failed:", R),
          (this._sqlJsFailed = !0));
      }
    if (
      (this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-loading",
        text: "Searching...",
      }),
      !u)
    ) {
      this._renderSearchError("Could not determine vault path");
      return;
    }
    let p = null,
      b = this.app.plugins;
    if (b && typeof b == "object" && "plugins" in b) {
      let R = b.plugins;
      if (R && typeof R == "object" && "paperforge" in R) {
        let S = R.paperforge;
        S && typeof S == "object" && "settings" in S && (p = S.settings);
      }
    }
    let { path: k, extraArgs: g = [] } = re(u, p, void 0, void 0),
      x = (0, et.spawn)(k, [...g, "-m", "paperforge", c, a, "--json"], {
        cwd: u,
        timeout: 3e4,
      }),
      C = [];
    (x.stdout.on("data", (R) => {
      C.push(R.toString("utf-8"));
    }),
      x.stderr.on("data", () => {}),
      x.on("close", (R) => {
        if (R !== 0) {
          this._renderSearchError(`Search failed (exit ${R})`);
          return;
        }
        let S = C.join(""),
          F = S.indexOf("{"),
          B = S.lastIndexOf("}"),
          A = "";
        if (F !== -1 && B > F) A = S.slice(F, B + 1);
        else {
          let v = S.indexOf("["),
            w = S.lastIndexOf("]");
          v !== -1 && w > v && (A = S.slice(v, w + 1));
        }
        if (!A) {
          this._renderSearchError("No JSON output from CLI");
          return;
        }
        try {
          let v = JSON.parse(A),
            w = [];
          if (v && typeof v == "object" && "data" in v) {
            let O = v.data;
            if (O && typeof O == "object") {
              let M = O;
              "matches" in M && Array.isArray(M.matches)
                ? (w = M.matches)
                : "results" in M && Array.isArray(M.results) && (w = M.results);
            }
          }
          this.renderSearchResults(w, i);
        } catch (v) {
          let w = v instanceof Error ? v.message : String(v);
          this._renderSearchError("Failed to parse results: " + w);
        }
      }),
      x.on("error", (R) => {
        this._renderSearchError("Process error: " + R.message);
      }));
  }
  renderSearchResults(r, n) {
    if (!this._searchResultsEl) return;
    if ((this._searchResultsEl.empty(), r.length === 0)) {
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-empty",
        text: "No results found.",
      });
      return;
    }
    let i = this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-results-header",
    });
    (i.createEl("span", {
      text: `${r.length} result${r.length !== 1 ? "s" : ""}`,
    }),
      i.createEl("span", {
        cls: "paperforge-search-mode",
        text: n ? "@" : "M",
      }));
    for (let a of r) {
      if (!a || typeof a != "object") continue;
      let c = a,
        l = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: { role: "button" },
        }),
        u =
          typeof c.title == "string"
            ? c.title
            : typeof c.file_name == "string"
              ? c.file_name
              : "(untitled)";
      l.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let p = typeof c.zotero_key == "string" ? c.zotero_key : "",
        h =
          typeof c.main_note_path == "string" && c.main_note_path
            ? c.main_note_path
            : null,
        b = typeof c.note_path == "string" && c.note_path ? c.note_path : null,
        k = h || b;
      if (!k && p) {
        let C = this._getCachedIndex().find(
          (R) =>
            R !== null &&
            typeof R == "object" &&
            "zotero_key" in R &&
            R.zotero_key === p
        );
        if (C && typeof C == "object") {
          let R = C;
          k =
            typeof R.main_note_path == "string" && R.main_note_path
              ? R.main_note_path
              : typeof R.note_path == "string" && R.note_path
                ? R.note_path
                : null;
        }
      }
      k
        ? l.addEventListener("click", (x) => {
            let C = x.ctrlKey || x.metaKey;
            this.app.workspace.openLinkText(k, "", C);
          })
        : l.addEventListener("click", () => {
            new X.Notice("[!!] Note not found: " + (p || "unknown"), 6e3);
          });
      let g = l.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof c.authors == "string"
          ? g.createEl("span", {
              cls: "paperforge-search-result-author",
              text: c.authors,
            })
          : Array.isArray(c.authors) &&
            g.createEl("span", {
              cls: "paperforge-search-result-author",
              text: c.authors.slice(0, 3).join("; "),
            }),
        (typeof c.year == "number" || typeof c.year == "string") &&
          g.createEl("span", {
            cls: "paperforge-search-result-year",
            text: String(c.year),
          }),
        typeof c.journal == "string" &&
          c.journal &&
          g.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: c.journal,
          }),
        c.score !== void 0)
      ) {
        let x = c.score,
          C = typeof x == "number" ? x.toFixed(3) : String(x);
        g.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + C,
        });
      }
      if (
        (typeof c.domain == "string" &&
          c.domain &&
          l.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: c.domain,
          }),
        typeof c.abstract == "string" && c.abstract)
      ) {
        let x = c.abstract;
        l.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: x.length > 200 ? x.slice(0, 200) + "..." : x,
        });
      }
      if (n && typeof c.matched_text == "string" && c.matched_text) {
        let x = c.matched_text;
        l.createEl("div", {
          cls: "paperforge-search-result-source",
          text: x.length > 300 ? x.slice(0, 300) + "..." : x,
        });
      }
    }
  }
  _renderSearchError(r) {
    this._searchResultsEl &&
      (this._searchResultsEl.empty(),
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-error",
        text: r,
      }));
  }
  _runAction(r, n) {
    var g, x;
    if (r.disabled) {
      new X.Notice(
        `[i] ${r.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (n.classList.contains("running")) return;
    n.addClass("running");
    let i = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let a = Array.isArray(r.args) ? [...r.args] : [];
    if (r.needsKey) {
      let C = this.app.workspace.getActiveFile(),
        R = null;
      if (C) {
        let S = this.app.metadataCache.getFileCache(C);
        if (
          (S && S.frontmatter && S.frontmatter.zotero_key
            ? (R = S.frontmatter.zotero_key)
            : (R = this._extractZoteroKeyFromPath(C.path)),
          R)
        )
          a = [...a, R];
        else if (S && S.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new X.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            n.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new X.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            n.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new X.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          n.removeClass("running"));
        return;
      }
    }
    r.needsFilter && (a = [...a, "--all"]);
    let c = r.needsFilter ? 6e4 : r.needsKey ? 3e4 : 6e5,
      { path: l, extraArgs: u = [] } = re(
        i,
        (x =
          (g = this.app.plugins.plugins.paperforge) == null
            ? void 0
            : g.settings) != null
          ? x
          : null,
        void 0,
        void 0
      ),
      p = (0, et.spawn)(l, [...u, "-m", "paperforge", r.cmd, ...a], {
        cwd: i,
        timeout: c,
      }),
      h = [],
      b = Date.now(),
      k = setInterval(() => this._fetchStats(!0), 4e3);
    (p.stdout.on("data", (C) => {
      let R = C.toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let S of R) {
        let F = S.trim();
        F &&
          (h.push(F),
          this._showMessage(
            h.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      p.stderr.on("data", (C) => {
        let R = C.toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let S of R) {
          if (S.includes("\r") || S.includes("%") || S.includes("\u2588"))
            continue;
          let F = S.trim();
          F &&
            !F.match(/^\d+%|^\|/) &&
            (h.push(F),
            this._showMessage(
              h.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      p.on("close", (C) => {
        (clearInterval(k), n.removeClass("running"));
        let R = ((Date.now() - b) / 1e3).toFixed(1);
        if (C !== 0) {
          let S = h.slice(-3).join(" | ") || "exit code " + C;
          (r.cmd === "repair" || r.cmd === "ocr") && C === 1
            ? (this._showMessage("[WARN] " + S, "running"),
              new X.Notice("[WARN] " + r.cmd + " partial: " + S, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + S, "error"),
              new X.Notice("[!!] " + r.cmd + " failed: " + S, 8e3));
        } else if (r.needsKey || r.needsFilter) {
          let S = h.join(`
`);
          if (S.trim())
            try {
              (JSON.parse(S),
                navigator.clipboard
                  .writeText(S)
                  .then(() => {
                    let F = `${R}s \u2014 ${S.length} chars copied`;
                    (this._showMessage("[OK] " + r.title + ": " + F, "ok"),
                      new X.Notice(
                        "[OK] " + r.okMsg + " \u2014 " + S.length + " chars"
                      ));
                  })
                  .catch((F) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + F.message,
                      "error"
                    ),
                      new X.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (F) {
              (this._showMessage("[!!] Invalid JSON from " + r.title, "error"),
                new X.Notice(
                  "[!!] " +
                    r.title +
                    " returned invalid JSON: " +
                    F.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new X.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let F =
              h.filter((A) => A.match(/updated \d+/)).pop() ||
              h[h.length - 1] ||
              "",
            B = `${R}s \u2014 ${F}`;
          (this._showMessage("[OK] " + r.title + ": " + B, "ok"),
            new X.Notice("[OK] " + r.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (A) {
            console.log("[PF] fetchStats error:", A);
          }
          (console.log("[PF] close cmd=" + r.cmd + " id=" + r.id),
            r.cmd === "sync" &&
              Qt(this.app, this.app.plugins.plugins.paperforge, i));
        }
      }),
      p.on("error", (C) => {
        (n.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + C.message, "error"),
          new X.Notice("[!!] Cannot start: " + C.message, 8e3));
      }));
  }
  _showMessage(r, n) {
    this._messageEl &&
      (this._messageEl.setText(r),
      (this._messageEl.className = `paperforge-message msg-${n}`));
  }
  _renderModeHeader(r) {
    if (!this._modeContextEl) return;
    this._modeContextEl.empty();
    let n = this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-badge",
      }),
      i = "";
    switch (r) {
      case "global":
        (n.addClass("global"),
          n.setText("Global"),
          this._headerTitle && this._headerTitle.setText("PaperForge"));
        break;
      case "paper":
        (n.addClass("paper"),
          n.setText("Paper"),
          this._headerTitle && this._headerTitle.setText("Paper"),
          this._currentPaperEntry && this._currentPaperEntry.title
            ? (i = this._currentPaperEntry.title)
            : this._currentPaperKey
              ? ((i = this._currentPaperKey),
                this._modeContextEl.createEl("span", {
                  cls: "paperforge-mode-warning",
                  text: "Not found in index",
                }))
              : (i = "Unknown paper"));
        break;
      case "collection":
        (n.addClass("collection"),
          n.setText("Collection"),
          this._headerTitle && this._headerTitle.setText("Collection"),
          (i = this._currentDomain || "Unknown Domain"));
        break;
      case "versions":
        (n.addClass("versions"),
          n.setText(f("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(f("version_panel_title")));
        break;
    }
    i &&
      this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-name",
        text: i,
      });
  }
  _setupEventSubscriptions() {
    let r = this.app.workspace.on("active-leaf-change", () => {
      (this._leafChangeTimer && clearTimeout(this._leafChangeTimer),
        (this._leafChangeTimer = setTimeout(() => {
          let i = this._resolveModeForFile(this.app.workspace.getActiveFile()),
            a = i.mode,
            c = i.filePath;
          (this._currentMode === a && this._currentFilePath === c) ||
            this._detectAndSwitch();
        }, 300)));
    });
    this._modeSubscribers.push({ event: "active-leaf-change", ref: r });
    let n = this.app.vault.on("modify", (i) => {
      i &&
        i.path &&
        i.path.endsWith("formal-library.json") &&
        (this._invalidateIndex(), this._refreshCurrentMode());
    });
    this._modeSubscribers.push({ event: "modify", ref: n });
  }
  static async open(r) {
    let n = r.app.workspace.getLeavesOfType(it);
    if (n.length > 0) {
      r.app.workspace.revealLeaf(n[0]);
      return;
    }
    let i = r.app.workspace.getRightLeaf(!1);
    i &&
      (await i.setViewState({ type: it, active: !0 }),
      r.app.workspace.revealLeaf(i));
  }
};
var ar = class extends de.Plugin {
  constructor() {
    super(...arguments);
    this._lastExportMtime = 0;
    this._lastOcrMtimes = {};
    this._autoSyncRunning = !1;
    this._lastSyncTime = null;
    this._pollTimer = null;
    this._embedProcess = null;
    this._embedProgress = { current: 0, total: 0, key: "" };
    this._embedStderr = "";
    this._memoryStatusText = null;
  }
  async onload() {
    (await this.loadSettings(),
      this.saveSettings(),
      kn(this.app),
      this.registerView(it, (n) => new yt(n)));
    try {
      (0, de.addIcon)(Ct, xn);
    } catch (n) {}
    (this.addRibbonIcon(Ct, "PaperForge Dashboard", () => yt.open(this)),
      Pe.find((n) => n.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", () => {
          let n = this.app.vault.adapter.basePath;
          new de.Notice("PaperForge: Redo OCR starting...");
          let { path: i, extraArgs: a } = re(n, this.settings, void 0, void 0);
          (0, He.execFile)(
            i,
            [...a, "-m", "paperforge", "ocr", "redo"],
            { cwd: n, timeout: 6e5 },
            (c, l, u) => {
              if (c) {
                new de.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new de.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new er(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${f("guide_open")}`,
        callback: () => yt.open(this),
      }));
    for (let n of Pe)
      this.addCommand({
        id: n.id,
        name: `PaperForge: ${n.title}`,
        callback: () => {
          if (n.disabled) {
            new de.Notice(
              `[i] ${n.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let i = this.app.vault.adapter.basePath;
          new de.Notice(`PaperForge: running ${n.cmd}...`);
          let { path: a, extraArgs: c = [] } = re(
              i,
              this.settings,
              void 0,
              void 0
            ),
            l = Array.isArray(n.args) ? [...n.args] : [];
          (0, He.execFile)(
            a,
            [...c, "-m", "paperforge", n.cmd, ...l],
            { cwd: i, timeout: 3e5 },
            (u, p, h) => {
              if (u) {
                new de.Notice(
                  `[!!] ${n.cmd} failed: ${(h || u.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new de.Notice(
                `[OK] ${
                  n.okMsg ||
                  p
                    .trim()
                    .split(
                      `
`
                    )[0]
                    .slice(0, 80)
                }`
              );
            }
          );
        },
      });
    (this.settings.auto_update_on_startup === !0 &&
      this.settings.setup_complete &&
      setTimeout(() => this._autoUpdate(), 3e3),
      this._startFilePolling(),
      this._firstLaunchSnapshotMigration(),
      this._checkReleaseNotes());
  }
  _firstLaunchSnapshotMigration() {
    let r = this.app.vault.adapter.basePath;
    if (!r) return;
    let i = Te(r).memoryStatePath;
    if (!le.existsSync(i)) {
      let a = re(r, this.settings, void 0, void 0);
      [
        ["runtime-health", "--json"],
        ["memory", "status", "--json"],
        ["embed", "status", "--json"],
      ].forEach((l) => {
        let u = [...a.extraArgs, "-m", "paperforge", "--vault", r, ...l];
        (0, He.execFile)(
          a.path,
          u,
          { cwd: r, timeout: 6e4, windowsHide: !0 },
          () => {}
        );
      });
    }
  }
  _autoUpdate() {
    let r = this.app.vault.adapter.basePath,
      { path: n, extraArgs: i = [] } = re(r, this.settings, void 0, void 0),
      a = this.manifest.version,
      c = `paperforge==${a}`,
      l = `git+https://github.com/LLLin000/PaperForge.git@${a}`,
      u = (p, h) => {
        (0, He.spawn)(n, [...i, "-m", "pip", "install", "--upgrade", p], {
          cwd: r,
          timeout: 12e4,
          env: ot(),
        }).on("close", (k) => h(k === 0));
      };
    (0, He.execFile)(
      n,
      [...i, "-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: r, timeout: 1e4 },
      (p, h) => {
        let b = (g) => {
          (console.log(
            `[PaperForge] Auto-update: trying PyPI (paperforge==${a})`
          ),
            u(c, (x) => {
              if (x) {
                (console.log("[PaperForge] Auto-update: installed via PyPI"),
                  new de.Notice(`[OK] PaperForge CLI ${g}`, 5e3));
                return;
              }
              (console.warn(
                "[PaperForge] Auto-update: PyPI failed, falling back to git..."
              ),
                u(l, (C) => {
                  C &&
                    (console.log("[PaperForge] Auto-update: installed via git"),
                    new de.Notice(`[OK] PaperForge CLI ${g} (via git)`, 5e3));
                }));
            }));
        };
        if (p) {
          b("installed");
          return;
        }
        let k = h.trim();
        k !== a && b(`${k} -> ${a}`);
      }
    );
  }
  _startFilePolling() {
    let r = this.app.vault.adapter.basePath;
    this._pollTimer = setInterval(() => {
      (this._checkExports(r), this._checkOcr(r));
    }, 12e4);
  }
  _checkExports(r) {
    if (this._autoSyncRunning) return;
    let n = Te(r).exportsDir;
    if (!le.existsSync(n)) return;
    let i = 0;
    try {
      le.readdirSync(n).forEach((a) => {
        if (!a.endsWith(".json")) return;
        let c = le.statSync(bt.join(n, a));
        c.mtimeMs > i && (i = c.mtimeMs);
      });
    } catch (a) {
      return;
    }
    i > this._lastExportMtime &&
      ((this._lastExportMtime = i), this._autoSync(r));
  }
  _autoSync(r) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = !0;
    let n = re(r, this.settings, void 0, void 0);
    if (!n.path) {
      this._autoSyncRunning = !1;
      return;
    }
    let i = `"${n.path}" -m paperforge --vault "${r}" sync`;
    (0, He.exec)(i, { timeout: 12e4, encoding: "utf-8" }, (a, c, l) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        a || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let u = Te(r).exportsDir,
          p = 0;
        (le.readdirSync(u).forEach((h) => {
          h.endsWith(".json") &&
            (p = Math.max(p, le.statSync(bt.join(u, h)).mtimeMs));
        }),
          (this._lastExportMtime = p));
      } catch (u) {}
    });
  }
  _checkOcr(r) {
    if (this._autoSyncRunning) return;
    let n = Te(r).ocrDir;
    if (le.existsSync(n))
      try {
        le.readdirSync(n, { withFileTypes: !0 }).forEach((i) => {
          if (!i.isDirectory()) return;
          let a = bt.join(n, i.name, "meta.json");
          if (!le.existsSync(a)) return;
          let c = le.statSync(a),
            l = this._lastOcrMtimes[i.name] || 0;
          if (
            c.mtimeMs <= l ||
            ((this._lastOcrMtimes[i.name] = c.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let u = re(r, this.settings, void 0, void 0);
          if (!u.path) {
            this._autoSyncRunning = !1;
            return;
          }
          let p = `"${u.path}" -m paperforge --vault "${r}" sync`;
          (0, He.exec)(p, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (i) {}
  }
  readPaperforgeJson() {
    let r = this.app.vault.adapter.basePath,
      n = bt.join(r, "paperforge.json"),
      i = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
      };
    try {
      if (!le.existsSync(n)) return i;
      let a = le.readFileSync(n, "utf-8"),
        c = JSON.parse(a),
        l = c.vault_config || {};
      return {
        system_dir: l.system_dir || c.system_dir || i.system_dir,
        resources_dir: l.resources_dir || c.resources_dir || i.resources_dir,
        literature_dir:
          l.literature_dir || c.literature_dir || i.literature_dir,
        base_dir: l.base_dir || c.base_dir || i.base_dir,
      };
    } catch (a) {
      return (
        console.warn(
          "PaperForge: Failed to read paperforge.json, using defaults",
          a
        ),
        i
      );
    }
  }
  savePaperforgeJson(r) {
    let n = this.app.vault.adapter.basePath,
      i = bt.join(n, "paperforge.json"),
      a = {};
    try {
      le.existsSync(i) && (a = JSON.parse(le.readFileSync(i, "utf-8")));
    } catch (l) {
      console.warn("PaperForge: Failed to read paperforge.json for update", l);
    }
    (!a.vault_config || typeof a.vault_config != "object") &&
      (a.vault_config = {});
    let c = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let l of c) r[l] !== void 0 && (a.vault_config[l] = r[l]);
    a.schema_version || (a.schema_version = "2");
    for (let l of c) delete a[l];
    try {
      if (
        (le.writeFileSync(i, JSON.stringify(a, null, 2), "utf-8"),
        this.settings)
      ) {
        let l = this.readPaperforgeJson();
        ((this.settings.system_dir = l.system_dir),
          (this.settings.resources_dir = l.resources_dir),
          (this.settings.literature_dir = l.literature_dir),
          (this.settings.base_dir = l.base_dir));
      }
    } catch (l) {
      (console.error("PaperForge: Failed to write paperforge.json", l),
        new de.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(it));
  }
  async loadSettings() {
    ((this.settings = Object.assign({}, Ft, await this.loadData())),
      this.settings.features &&
        Ft.features &&
        (this.settings.features = Object.assign(
          {},
          Ft.features,
          this.settings.features || {}
        )),
      this.settings.frozen_skills || (this.settings.frozen_skills = {}));
    let r = this.readPaperforgeJson();
    if (
      ((this.settings.system_dir = r.system_dir),
      (this.settings.resources_dir = r.resources_dir),
      (this.settings.literature_dir = r.literature_dir),
      (this.settings.base_dir = r.base_dir),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let n = this.settings.python_path.trim();
      le.existsSync(n)
        ? (this.settings._python_path_stale = !1)
        : (console.warn(
            `PaperForge: Saved python_path "${n}" no longer exists - showing stale warning`
          ),
          (this.settings._python_path_stale = !0));
    }
  }
  async saveSettings() {
    let r = {};
    for (let n of Object.keys(Ft))
      n in this.settings && (r[n] = this.settings[n]);
    await this.saveData(r);
  }
  _checkReleaseNotes() {
    let r = this.manifest.version;
    if (this.settings.last_seen_version === r) return;
    let c = (Sr().versions || []).find((u) => u.version === r);
    class l extends de.Modal {
      constructor(p, h) {
        (super(p), (this._entry = h));
      }
      onOpen() {
        let { contentEl: p } = this;
        if (
          (p.createEl("h2", {
            text: `PaperForge v${r} \u66F4\u65B0\u8BF4\u660E`,
          }),
          this._entry)
        ) {
          if (
            (p.createEl("p", {
              text: this._entry.title,
              cls: "paperforge-modal-subtitle",
            }),
            this._entry.breaking_or_migration &&
              this._entry.breaking_or_migration.length > 0)
          ) {
            p.createEl("h4", {
              text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
            });
            for (let h of this._entry.breaking_or_migration)
              p.createEl("p", {
                text: `\u2022 ${h}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            p.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let h of this._entry.new_features)
              p.createEl("p", {
                text: `\u2022 ${h}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            p.createEl("h4", { text: "\u4FEE\u590D" });
            for (let h of this._entry.fixes)
              p.createEl("p", {
                text: `\u2022 ${h}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let h = p.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            (h.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
              (h.style.marginBottom = "8px"));
            for (let b of this._entry.recommended_actions)
              h.createEl("p", {
                text: `\u2022 ${b}`,
                cls: "paperforge-release-item-bold",
              });
          }
        } else
          p.createEl("p", {
            text:
              "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
              r +
              "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
          });
        new de.Setting(p).addButton((h) =>
          h
            .setButtonText("\u77E5\u9053\u4E86")
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        let { contentEl: p } = this;
        p.empty();
      }
    }
    (new l(this.app, c).open(),
      (this.settings.last_seen_version = r),
      this.saveSettings());
  }
};
