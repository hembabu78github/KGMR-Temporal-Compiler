import json,re

_SAFE_KEY=re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")

def _scalar(v):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v,bool):
        return "true" if v else "false"
    if isinstance(v,int):
        return str(v)
    if isinstance(v,float):
        s=json.dumps(v,allow_nan=False)
        # YAML 1.1 parsers such as PyYAML may treat `1e-09` as a string.
        # Emit `1.0e-09`, which is numeric in both YAML 1.1 and YAML 1.2.
        if ("e" in s or "E" in s):
            marker="e" if "e" in s else "E"
            mant,exp=s.split(marker,1)
            if "." not in mant:
                mant=mant+".0"
            s=mant+"e"+exp
        return s
    # JSON-quoted strings are valid YAML scalars and preserve escaping deterministically.
    return json.dumps(str(v),ensure_ascii=False)

def _key(k):
    s=str(k)
    return s if _SAFE_KEY.match(s) else json.dumps(s,ensure_ascii=False)

def dump_yaml(obj,indent=0):
    sp=" " * indent
    if isinstance(obj,dict):
        if not obj: return "{}"
        lines=[]
        for k in obj:
            v=obj[k]
            if isinstance(v,(dict,list)) and v:
                lines.append(f"{sp}{_key(k)}:")
                lines.append(dump_yaml(v,indent+2))
            else:
                rendered=dump_yaml(v,0) if isinstance(v,(dict,list)) else _scalar(v)
                lines.append(f"{sp}{_key(k)}: {rendered}")
        return "\n".join(lines)
    if isinstance(obj,list):
        if not obj: return "[]"
        lines=[]
        for v in obj:
            if isinstance(v,(dict,list)) and v:
                lines.append(f"{sp}-")
                lines.append(dump_yaml(v,indent+2))
            else:
                rendered=dump_yaml(v,0) if isinstance(v,(dict,list)) else _scalar(v)
                lines.append(f"{sp}- {rendered}")
        return "\n".join(lines)
    return sp+_scalar(obj)

def dumps_yaml_document(obj):
    return "---\n"+dump_yaml(obj,0)+"\n"


def _parse_yaml_scalar(text):
    text=text.strip()
    if text=="{}": return {}
    if text=="[]": return []
    # All non-container scalars emitted by this module are valid JSON scalars.
    return json.loads(text)

def loads_deterministic_yaml_document(text):
    """
    Parse only the deterministic YAML subset produced by dumps_yaml_document().
    This is intentionally not a general YAML parser.
    """
    raw=text.replace("\r\n","\n").splitlines()
    lines=[]
    for line in raw:
        if not line.strip() or line.strip()=="---":
            continue
        indent=len(line)-len(line.lstrip(" "))
        lines.append((indent,line.strip()))

    def parse_block(i,indent):
        if i>=len(lines) or lines[i][0] < indent:
            return None,i
        is_list=lines[i][1].startswith("-")
        if is_list:
            out=[]
            while i<len(lines) and lines[i][0]==indent and lines[i][1].startswith("-"):
                token=lines[i][1]
                if token=="-":
                    child,i=parse_block(i+1,indent+2)
                    out.append(child)
                else:
                    out.append(_parse_yaml_scalar(token[1:].strip()))
                    i+=1
            return out,i

        out={}
        while i<len(lines) and lines[i][0]==indent and not lines[i][1].startswith("-"):
            token=lines[i][1]
            key,rest=token.split(":",1)
            key=key.strip()
            if key.startswith('"'):
                key=json.loads(key)
            rest=rest.strip()
            if rest=="":
                child,i=parse_block(i+1,indent+2)
                out[key]=child
            else:
                out[key]=_parse_yaml_scalar(rest)
                i+=1
        return out,i

    if not lines:
        return None
    value,index=parse_block(0,lines[0][0])
    if index!=len(lines):
        raise ValueError("Unparsed deterministic YAML content remains")
    return value
