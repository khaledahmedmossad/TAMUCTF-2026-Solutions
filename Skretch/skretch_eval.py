import json
import math
import sys
import zipfile


PROJECT = "/Users/goku/Documents/New project/tmp/skretch/skretch_FULL.sb3"


def to_num(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    if v is None:
        return 0
    s = str(v).strip()
    if s == "":
        return 0
    try:
        if s == "Infinity":
            return float("inf")
        if s == "-Infinity":
            return float("-inf")
        if s == "NaN":
            return float("nan")
        if any(c in s for c in ".eE"):
            return float(s)
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0


def scratch_str(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        if v.is_integer():
            return str(int(v))
        return str(v)
    return str(v)


def to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v)
    return s.lower() not in ("", "0", "false")


def scratch_eq(a, b):
    try:
        return float(scratch_str(a)) == float(scratch_str(b))
    except Exception:
        return scratch_str(a) == scratch_str(b)


def scratch_lt(a, b):
    try:
        return float(scratch_str(a)) < float(scratch_str(b))
    except Exception:
        return scratch_str(a) < scratch_str(b)


def scratch_gt(a, b):
    try:
        return float(scratch_str(a)) > float(scratch_str(b))
    except Exception:
        return scratch_str(a) > scratch_str(b)


class VM:
    def __init__(self, data, file_value):
        self.data = data
        self.stage = data["targets"][0]
        self.sprite = data["targets"][1]
        self.blocks = self.sprite["blocks"]
        self.file_value = file_value
        self.vars = {}
        self.var_name_to_id = {}
        self.list_name_to_id = {}
        for target in data["targets"]:
            for vid, (name, val) in target.get("variables", {}).items():
                self.vars[vid] = val
                self.var_name_to_id[name] = vid
            for lid, (name, val) in target.get("lists", {}).items():
                self.vars[lid] = list(val)
                self.list_name_to_id[name] = lid
        self.current_backdrop = self.stage["currentCostume"] + 1
        self.say_log = []
        self.call_defs = {}
        for bid, b in self.blocks.items():
            if b["opcode"] == "procedures_definition":
                proto = b["inputs"]["custom_block"][1]
                proccode = self.blocks[proto]["mutation"]["proccode"]
                self.call_defs[proccode] = bid

    def input_ref(self, ref, proc_args=None):
        if proc_args is None:
            proc_args = {}
        kind = ref[0]
        if kind == 1:
            return ref[1][1]
        if kind == 2:
            return self.eval_block(ref[1], proc_args)
        if kind == 3:
            block = ref[1]
            if isinstance(block, list):
                if block[0] == 12:
                    return self.vars[block[2]]
                return block[-1]
            return self.eval_block(block, proc_args)
        raise ValueError(ref)

    def field_var_id(self, block, key):
        return block["fields"][key][1]

    def eval_block(self, bid, proc_args=None):
        if proc_args is None:
            proc_args = {}
        b = self.blocks[bid]
        op = b["opcode"]
        inp = b.get("inputs", {})
        if op == "files_showPickerAs":
            return self.file_value
        if op == "files_menu_encoding":
            return b["fields"]["encoding"][0]
        if op == "argument_reporter_string_number":
            return proc_args[b["fields"]["VALUE"][0]]
        if op == "operator_add":
            return to_num(self.input_ref(inp["NUM1"], proc_args)) + to_num(self.input_ref(inp["NUM2"], proc_args))
        if op == "operator_subtract":
            return to_num(self.input_ref(inp["NUM1"], proc_args)) - to_num(self.input_ref(inp["NUM2"], proc_args))
        if op == "operator_multiply":
            return to_num(self.input_ref(inp["NUM1"], proc_args)) * to_num(self.input_ref(inp["NUM2"], proc_args))
        if op == "operator_divide":
            a = to_num(self.input_ref(inp["NUM1"], proc_args))
            b2 = to_num(self.input_ref(inp["NUM2"], proc_args))
            if b2 == 0:
                if a == 0:
                    return float("nan")
                return float("inf") if a > 0 else float("-inf")
            return a / b2
        if op == "operator_mod":
            a = to_num(self.input_ref(inp["NUM1"], proc_args))
            b2 = to_num(self.input_ref(inp["NUM2"], proc_args))
            if b2 == 0:
                return float("nan")
            return a % b2
        if op == "operator_round":
            v = to_num(self.input_ref(inp["NUM"], proc_args))
            if math.isnan(v) or math.isinf(v):
                return v
            return round(v)
        if op == "operator_length":
            return len(scratch_str(self.input_ref(inp["STRING"], proc_args)))
        if op == "operator_join":
            return scratch_str(self.input_ref(inp["STRING1"], proc_args)) + scratch_str(self.input_ref(inp["STRING2"], proc_args))
        if op == "operator_letter_of":
            idx = int(to_num(self.input_ref(inp["LETTER"], proc_args)))
            s = scratch_str(self.input_ref(inp["STRING"], proc_args))
            if 1 <= idx <= len(s):
                return s[idx - 1]
            return ""
        if op == "operator_equals":
            return scratch_eq(self.input_ref(inp["OPERAND1"], proc_args), self.input_ref(inp["OPERAND2"], proc_args))
        if op == "operator_lt":
            return scratch_lt(self.input_ref(inp["OPERAND1"], proc_args), self.input_ref(inp["OPERAND2"], proc_args))
        if op == "operator_gt":
            return scratch_gt(self.input_ref(inp["OPERAND1"], proc_args), self.input_ref(inp["OPERAND2"], proc_args))
        if op == "operator_not":
            return not to_bool(self.input_ref(inp["OPERAND"], proc_args))
        if op == "operator_mathop":
            v = to_num(self.input_ref(inp["NUM"], proc_args))
            which = b["fields"]["OPERATOR"][0]
            if which == "floor":
                if math.isnan(v) or math.isinf(v):
                    return v
                return math.floor(v)
            if which == "abs":
                return abs(v)
            if which == "sqrt":
                return math.sqrt(v)
            if which == "ln":
                return math.log(v)
            if which == "10 ^":
                return 10 ** v
            if which == "e ^":
                return math.e ** v
            if which == "tan":
                return math.tan(math.radians(v))
            raise NotImplementedError(which)
        if op == "data_itemoflist":
            idx = int(to_num(self.input_ref(inp["INDEX"], proc_args)))
            lst = self.vars[self.field_var_id(b, "LIST")]
            if 1 <= idx <= len(lst):
                return lst[idx - 1]
            return ""
        if op == "data_lengthoflist":
            return len(self.vars[self.field_var_id(b, "LIST")])
        if op == "looks_backdropnumbername":
            mode = b["fields"]["NUMBER_NAME"][0]
            if mode == "number":
                return self.current_backdrop
            if mode == "name":
                return self.stage["costumes"][self.current_backdrop - 1]["name"]
            raise NotImplementedError(mode)
        if op == "looks_backdrops":
            return b["fields"]["BACKDROP"][0]
        raise NotImplementedError(("eval", op, bid))

    def exec_chain(self, start, proc_args=None, limit=10_000_000):
        if proc_args is None:
            proc_args = {}
        cur = start
        steps = 0
        while cur is not None:
            steps += 1
            if steps > limit:
                raise RuntimeError("step limit")
            b = self.blocks[cur]
            op = b["opcode"]
            inp = b.get("inputs", {})
            if op in ("event_whenflagclicked", "procedures_definition", "procedures_prototype"):
                pass
            elif op == "data_setvariableto":
                vid = self.field_var_id(b, "VARIABLE")
                self.vars[vid] = self.input_ref(inp["VALUE"], proc_args) if "VALUE" in inp else ""
            elif op == "data_changevariableby":
                vid = self.field_var_id(b, "VARIABLE")
                self.vars[vid] = to_num(self.vars[vid]) + to_num(self.input_ref(inp["VALUE"], proc_args))
            elif op == "data_deletealloflist":
                self.vars[self.field_var_id(b, "LIST")] = []
            elif op == "data_addtolist":
                self.vars[self.field_var_id(b, "LIST")].append(self.input_ref(inp["ITEM"], proc_args))
            elif op == "data_replaceitemoflist":
                lid = self.field_var_id(b, "LIST")
                idx = int(to_num(self.input_ref(inp["INDEX"], proc_args)))
                if 1 <= idx <= len(self.vars[lid]):
                    self.vars[lid][idx - 1] = self.input_ref(inp["ITEM"], proc_args)
            elif op == "control_repeat":
                n = int(to_num(self.input_ref(inp["TIMES"], proc_args)))
                for _ in range(max(n, 0)):
                    self.exec_chain(inp["SUBSTACK"][1], proc_args, limit)
            elif op == "control_while":
                while to_bool(self.eval_block(inp["CONDITION"][1], proc_args)):
                    self.exec_chain(inp["SUBSTACK"][1], proc_args, limit)
            elif op == "control_if_else":
                if to_bool(self.eval_block(inp["CONDITION"][1], proc_args)):
                    self.exec_chain(inp["SUBSTACK"][1], proc_args, limit)
                else:
                    self.exec_chain(inp["SUBSTACK2"][1], proc_args, limit)
            elif op == "procedures_call":
                proccode = b["mutation"]["proccode"]
                def_bid = self.call_defs[proccode]
                arg_ids = json.loads(b["mutation"]["argumentids"])
                arg_names = json.loads(self.blocks[self.blocks[def_bid]["inputs"]["custom_block"][1]]["mutation"]["argumentnames"])
                frame = {}
                for aid, name in zip(arg_ids, arg_names):
                    frame[name] = self.input_ref(inp[aid], proc_args)
                self.exec_chain(self.blocks[def_bid]["next"], frame, limit)
            elif op == "looks_switchbackdropto":
                val = self.input_ref(inp["BACKDROP"], proc_args)
                names = [c["name"] for c in self.stage["costumes"]]
                if isinstance(val, (int, float)):
                    self.current_backdrop = int(val)
                else:
                    sval = scratch_str(val)
                    if sval in names:
                        self.current_backdrop = names.index(sval) + 1
                    else:
                        raise ValueError(("bad backdrop", sval))
            elif op in ("looks_say", "looks_sayforsecs"):
                msg = self.input_ref(inp["MESSAGE"], proc_args)
                self.say_log.append(scratch_str(msg))
            else:
                raise NotImplementedError(("exec", op, cur))
            cur = b.get("next")


def main():
    file_value = sys.argv[1] if len(sys.argv) > 1 else "data:text/plain;base64,"
    with zipfile.ZipFile(PROJECT) as zf:
        with zf.open("project.json") as f:
            data = json.load(f)
    vm = VM(data, file_value)
    vm.exec_chain("ak")
    stage = data["targets"][0]
    print("say_log", vm.say_log)
    for vid, (name, _) in stage["variables"].items():
        print("VAR", name, repr(vm.vars[vid]))
    for lid, (name, _) in stage["lists"].items():
        print("LIST", name, len(vm.vars[lid]), vm.vars[lid][:10])
    sprite = data["targets"][1]
    for lid, (name, _) in sprite["lists"].items():
        print("SLIST", name, len(vm.vars[lid]), vm.vars[lid][:10])


if __name__ == "__main__":
    main()
