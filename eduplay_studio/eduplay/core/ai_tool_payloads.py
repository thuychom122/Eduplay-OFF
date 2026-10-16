def _parse_json_lenient(value):
    import json
    import ast

    try:
        raw = str(value or "").strip()
    except Exception:
        raw = ""
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
    candidates = []
    if raw:
        candidates.append(raw)
    try:
        i = raw.find("{")
        j = raw.rfind("}")
        if i != -1 and j != -1 and j > i:
            candidates.append(raw[i : j + 1])
    except Exception:
        pass
    try:
        i = raw.find("[")
        j = raw.rfind("]")
        if i != -1 and j != -1 and j > i:
            candidates.append(raw[i : j + 1])
    except Exception:
        pass
    try:
        raw2 = raw.replace("\r", "").replace("\n", " ").strip()
        if raw2 and raw2 not in candidates:
            candidates.append(raw2)
        try:
            i = raw2.find("{")
            j = raw2.rfind("}")
            if i != -1 and j != -1 and j > i:
                cand = raw2[i : j + 1]
                if cand not in candidates:
                    candidates.append(cand)
        except Exception:
            pass
        try:
            i = raw2.find("[")
            j = raw2.rfind("]")
            if i != -1 and j != -1 and j > i:
                cand = raw2[i : j + 1]
                if cand not in candidates:
                    candidates.append(cand)
        except Exception:
            pass
    except Exception:
        pass
    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            pass
        try:
            obj = ast.literal_eval(cand)
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:
            pass
    return None


def build_updated_question(payload, current_q):
    if not isinstance(payload, dict):
        return None

    patch = payload.get("patch")
    full = payload.get("question")

    if isinstance(patch, str):
        patch_s = patch
        patch = _parse_json_lenient(patch)
        if patch is None:
            try:
                ps = str(patch_s or "").strip()
            except Exception:
                ps = ""
            if ps:
                patch = {"explanation": ps}
    if isinstance(full, str):
        full = _parse_json_lenient(full)

    if isinstance(full, dict):
        return dict(full)

    if isinstance(patch, dict) and isinstance(current_q, dict):
        new_q = dict(current_q)
        new_q.update(patch)
        return new_q

    if isinstance(current_q, dict):
        ignore = {
            "question_id",
            "questionId",
            "qid",
            "id",
            "question_index",
            "questionIndex",
            "index",
            "question_number",
            "questionNumber",
            "number",
            "q",
            "patch",
            "question",
        }
        flat_patch = {}
        for k, v in payload.items():
            if k in ignore:
                continue
            flat_patch[k] = v
        if flat_patch:
            new_q = dict(current_q)
            new_q.update(flat_patch)
            return new_q

    return None


def parse_update_question_payload(args):
    if isinstance(args, dict):
        return args
    obj = _parse_json_lenient(args)
    if isinstance(obj, dict):
        return obj
    try:
        s = str(args or "").strip()
    except Exception:
        s = ""
    if not s:
        return {}
    if ":" in s and "{" in s:
        try:
            i = s.find("{")
            j = s.rfind("}")
            if i != -1 and j != -1 and j > i:
                cand = s[i : j + 1]
                obj2 = _parse_json_lenient(cand)
                if isinstance(obj2, dict):
                    return obj2
        except Exception:
            pass
    try:
        import re

        pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\".*?\"|\'.*?\'|[^,]+)", s)
        out = {}
        for k, v in pairs:
            key = str(k or "").strip()
            val_raw = str(v or "").strip()
            if (val_raw.startswith('"') and val_raw.endswith('"')) or (val_raw.startswith("'") and val_raw.endswith("'")):
                val = val_raw[1:-1]
            else:
                val = val_raw.strip()
            if key:
                out[key] = val
        if out:
            return out
        return {"patch": {"explanation": s}}
    except Exception:
        if s:
            return {"patch": {"explanation": s}}
        return {}


def extract_question_numbers(text):
    try:
        s = str(text or "")
    except Exception:
        s = ""
    if not s:
        return []
    try:
        import re
    except Exception:
        re = None
    nums = []
    if re is not None:
        for m in re.finditer(r"(?:\b(?:câu|cau|q)\s*#?\s*)(\d{1,3})\b", s, flags=re.IGNORECASE):
            nums.append(m.group(1))
        if not nums:
            for m in re.finditer(r"\bq(\d{1,3})\b", s, flags=re.IGNORECASE):
                nums.append(m.group(1))
        try:
            if ("câu" in s.lower()) or ("cau" in s.lower()):
                for m in re.finditer(r"\b(\d{1,3})\b", s):
                    nums.append(m.group(1))
        except Exception:
            pass
    seen = set()
    out = []
    for x in nums:
        try:
            n = int(str(x))
        except Exception:
            continue
        if n <= 0 or n > 500:
            continue
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def safe_calculate(expression: str):
    """Tính biểu thức toán học 1 cách an toàn (offline, đúng 100%).
    Hỗ trợ: + - * / % ^ ( ) số thập phân, x/X/× (nhân), :/÷ (chia), , (thập phân).
    Người dùng được gõ x thay * và : thay / , tự hiểu. Vd: 12x8:4 = 24.
    Trả về (ok: bool, cleaned_expr: str, result_or_error: Any).
    """
    import re as _re
    import ast as _ast
    try:
        raw = str(expression or "")
    except Exception:
        raw = ""
    if not raw.strip():
        return (False, "", "Thiếu biểu thức")
    try:
        e = raw.strip().lower()
        # Từ tiếng Việt phổ biến
        e = e.replace("cộng", "+").replace("cong", "+")
        e = e.replace("trừ", "-").replace("tru", "-")
        e = e.replace("nhân", "*").replace("nhan", "*")
        e = e.replace("chia", "/")
        e = e.replace("mũ", "**").replace("mu", "**")
        e = e.replace("×", "*").replace("÷", "/").replace(",", ".")
        # ':' là chia (12:4 = 12/4). Cả ':' thường và '：' fullwidth.
        e = e.replace("：", ":")
        # 'x' là nhân: 12x8, 12 x 8, (12+8)x2, 12x(8+1). Chỉ đổi khi kẹp giữa số/ngoặc.
        try:
            e = _re.sub(r"(?<=[\d\)\]])\s*[xX×]\s*(?=[\d\(\[])", "*", e)
        except Exception:
            pass
        try:
            e = _re.sub(r"(?<=[\d\)\]])\s*:\s*(?=[\d\(\[])", "/", e)
        except Exception:
            # fallback đơn giản: mọi ':' còn lại giữa số đều là chia
            try:
                e = _re.sub(r"(?<=\d)\s*:\s*(?=\d)", "/", e)
            except Exception:
                pass
        e = _re.sub(r"[^0-9\.\+\-\*\/\%\(\)\s\^]", "", e).strip()
        e = e.replace("^", "**")
        # bỏ dấu * / thừa đầu/cuối (vd: "*8+")
        e = e.strip("*/%+")
        if not e:
            return (False, "", "Không hiểu biểu thức")
        if not _re.search(r"\d", e):
            return (False, "", "Không hiểu biểu thức")
        _allowed = {
            _ast.Expression, _ast.BinOp, _ast.UnaryOp, _ast.Num, _ast.Constant,
            _ast.Add, _ast.Sub, _ast.Mult, _ast.Div, _ast.Mod, _ast.Pow,
            _ast.USub, _ast.UAdd, _ast.Load,
        }
        tree = _ast.parse(e, mode="eval")
        for n in _ast.walk(tree):
            if type(n) not in _allowed:
                return (False, e, "Biểu thức không an toàn")
        res = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}})
        # làm gọn số nguyên dạng 101.0 -> 101
        try:
            if isinstance(res, float) and res.is_integer():
                res = int(res)
        except Exception:
            pass
        return (True, e, res)
    except ZeroDivisionError:
        return (False, str(expression or "").strip(), "Không chia được cho 0")
    except SyntaxError:
        return (False, str(expression or "").strip(), "Biểu thức chưa đúng, ví dụ: 12*8+5")
    except Exception as ex:
        return (False, str(expression or "").strip(), str(ex) or "Biểu thức chưa đúng")


def extract_calc_expression(text: str):
    """Tách biểu thức toán từ tin nhắn chat.
    Nhận: 'tính 12*8+5', 'tinh 12x8+5', 'tính 12x8:4', 'calculate (12+8)/4', '12*8+5=?', '12:4=?', '=12x8'
    Người dùng được gõ x thay * và : thay / . Vd: 12x8:4 = 24.
    Trả về biểu thức hoặc ''.
    """
    import re as _re
    try:
        s = str(text or "").strip()
    except Exception:
        return ""
    if not s:
        return ""
    # Bỏ phần [ATTACHMENTS] nếu có
    try:
        s = s.split("[ATTACHMENTS]", 1)[0].strip()
    except Exception:
        pass
    low = s.lower()
    # Guard: 'tính năng / tinh nang' là hỏi tính năng, KHÔNG phải phép tính
    if "tính năng" in low or "tinh nang" in low:
        return ""
    # prefix tường minh
    prefixes = ("tính", "tinh", "calculate", "calc", "solve", "solve math", "kết quả", "ket qua", "bằng bao nhiêu", "bang bao nhieu")
    expr = ""
    for p in prefixes:
        if low.startswith(p):
            expr = s[len(p):].strip(" :ş=→>-–—?\"'").strip()
            break
    if not expr:
        # '12*8+5=?' hoặc chứa '=' -> lấy vế trái
        if "=" in s and any(ch.isdigit() for ch in s):
            left = s.split("=", 1)[0].strip()
            # chỉ nhận nếu vế trái trông như biểu thức (chấp nhận x và : )
            if any(ch.isdigit() for ch in left) and any(op in left for op in ("+", "-", "*", "/", "x", "X", "×", ":", "：", "÷", "^", "%", "(", "cộng", "trừ", "nhân", "chia")):
                expr = left.strip()
        else:
            # cả tin nhắn là biểu thức thuần? vd: '12*8+5', '12x8:4', '(12+8)/4'
            t = s.strip().rstrip("?").strip()
            if any(ch.isdigit() for ch in t):
                tmp = t.lower().replace("×", "*").replace("÷", "/").replace("：", ":")
                if _re.fullmatch(r"[\d\s\.\+\-\*\/\%\^\:\(\)xX×÷：]+", tmp) and _re.search(r"\d\s*[\+\-\*\/\%\^\:xX×÷]\s*\d", tmp):
                    expr = t
    return str(expr or "").strip()
