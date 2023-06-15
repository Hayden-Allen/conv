import csv
import os
import re
import json


# get name string with appropriate index appended
# used for names that do not have to be unique (so anything that's not a type)
platform_counts = {}
weapon_counts = {}
def get_indexed_name(name, counts):
    name_index = 0
    if(name in counts):
        name_index = counts[name]
        counts[name] += 1
    else:
        counts[name] = 0
    return f"{name}_{name_index}"

# print an error and terminate
def err(str):
    print(f"ERROR: {str}")
    exit(1)

# traverses given directory and returns a list of all tokens in all files
def get_tokens(path):
    # empty line regex
    ws = r"^\s*$"
    # list of all tokens in all files in given dir
    all_tokens = []
    # recursively visits everything in directory `path`
    for root, dirs, files in os.walk(path):
        for file in files:
            # only get tokens from .txt files
            if(not file.endswith('.txt')):
                continue
            with open(f"{root}\{file}", "r") as f:
                # list of all lines
                lines = f.readlines()
                # remove multiline comments
                sanstr = re.sub(r"/\*[^*]*\*/", "", "\n".join(lines))
                # list of all lines without multiline comments
                lines = sanstr.split("\n")
                # list of tokens in current file
                tokens = []
                for line in lines:
                    # trim whitespace
                    sanline = line.strip()
                    # ignore single line comments
                    if(re.findall(ws, sanline) or sanline.startswith('#') or sanline.startswith('//')):
                        continue
                    # split current line into component tokens
                    cur_tokens = re.split(r"\s+", sanline)
                    tokens += cur_tokens
                all_tokens += tokens
    return all_tokens

# get or create parameter list of given name
def get_params(caller, name):
    if(not "__params__" in caller):
        caller["__params__"] = {}
    if(not name in caller["__params__"]):
        caller["__params__"][name] = []
    return caller["__params__"][name]

# for object instantiations. Get the object's type's default value for a parameter
types = None
def get_default_param(caller_end_token, param, type):
    caller_type = caller_end_token[(caller_end_token.find('_') + 1):]
    if(caller_type in types and "__params__" in types[caller_type][type]):
        return types[caller_type][type]["__params__"][param]
    return None





# parse weapon object definitions
def parse_weapon(tokens, start_index):
    result = {
        "weapon": {}
    }
    params = {
        "range": 2
    }
    def on_enter(tokens, start_index, result):
        if(start_index + 2 >= len(tokens)):
            err("Invalid weapon definition")
        name = get_indexed_name(tokens[start_index + 0], weapon_counts)
        type = tokens[start_index + 1]
        result["weapon"][name] = { "Name": name, "Type": type }
        return (start_index + 2, result["weapon"][name])
    return parse(
        tokens,
        start_index,
        result,
        {},
        params,
        "end_weapon",
        on_enter
    )

# parse weapon type definitions
def parse_named_weapon(tokens, start_index):
    result = {
        "weapon_type": {}
    }
    params = {
        "range": 2
    }
    def on_enter(tokens, start_index, result):
        if(start_index + 2 >= len(tokens)):
            err("Invalid weapon type definition")
        type = tokens[start_index + 0]
        base = tokens[start_index + 1]
        result["weapon_type"][type] = { "Type": type, "Base": base }
        return (start_index + 2, result["weapon_type"][type])
    return parse(
        tokens,
        start_index,
        result,
        {},
        params,
        "end_weapon",
        on_enter
    )

# parse platform object definitions
def parse_platform(tokens, start_index):
    result = {
        "platform": {},
        "weapon": {},
        "weapon_effects": {}
    }
    params = {
        "weapon_effects": 1
    }
    keyword_functions = {
        "weapon": parse_weapon
    }
    def on_enter(tokens, start_index, result):
        if(start_index + 2 >= len(tokens)):
            err("Invalid platform definition")
        name = get_indexed_name(tokens[start_index + 0], platform_counts)
        type = tokens[start_index + 1]
        result["platform"][name] = { "Name": name, "Type": type }
        return (start_index + 2, result["platform"][name])
    return parse(
        tokens,
        start_index,
        result,
        keyword_functions,
        params,
        "end_platform",
        on_enter
    )

# parse platform_type definitions
def parse_named_platform(tokens, start_index):
    result = {
        "platform_type": {},
        "weapon": {},
    }
    params = {
        "weapon_effects": 1
    }
    keyword_functions = {
        "weapon": parse_weapon,
    }
    def on_enter(tokens, start_index, result):
        if(start_index + 2 >= len(tokens)):
            err("Invalid platform_type definition")
        type = tokens[start_index + 0]
        base = tokens[start_index + 1]
        result["platform_type"][type] = { "Type": type, "Base": base }
        return (start_index + 2, result["platform_type"][type])
    return parse(
        tokens,
        start_index,
        result,
        keyword_functions,
        params,
        "end_platform_type",
        on_enter
    )

# parse weapon_effect type definitions
def parse_named_weapon_effects(tokens, start_index):
    result = {
        "weapon_effects_type": {}
    }
    params = {
        "radius_and_pk": (2, 1),
        "range": 2
    }
    def on_enter(tokens, start_index, result):
        type = tokens[start_index + 0]
        base = tokens[start_index + 1]
        result["weapon_effects_type"][type] = { "Type": type, "Base": base }
        return (start_index + 2, result["weapon_effects_type"][type])
    return parse(
        tokens,
        start_index,
        result,
        {},
        params,
        "end_weapon_effects",
        on_enter
    )
  
# parse all files from the top level
def parse_all(tokens):
    result = {
        "platform": {},
        "platform_type": {},
        "weapon": {},
        "weapon_type": {},
        "weapon_effects_type": {},
    }
    keyword_functions = {
        "platform": parse_platform,
        "platform_type": parse_named_platform,
        "weapon": (parse_named_weapon, "weapon_type"),
        "weapon_effects": (parse_named_weapon_effects, "weapon_effects_type")
    }
    return parse(
        tokens,
        0,
        result,
        keyword_functions,
        None,
        None,
        lambda t, s, r: (s, None)
    )[0]

# generic parsing function
def parse(tokens, start_index, result, keyword_functions, params, end_token, on_enter):
    # processes the first line of an object definition such as:
    #   weapon w1 TEST_WEAPON
    #           OR
    #   platform p1 WSF_PLATFORM
    (index, caller) = on_enter(tokens, start_index, result)
    # read all tokens
    while(index < len(tokens)):
        cur = tokens[index]
        # skip includes (all files are accounted for already)
        if(cur == "include_once"):
            index += 2
            continue
        # if current token is the end token for this block, return
        if(cur == end_token):
            # insert default parameters if necessary
            if(len(params) and types):
                if(not "__params__" in caller):
                    caller["__params__"] = {}
                for param, val in params.items():
                    if(not param in caller["__params__"]):
                        default_param = get_default_param(end_token, param, caller["Type"])
                        if(default_param):
                            caller["__params__"][param] = default_param
            break
        #print(f"parse: {index} | {cur}")
        # if current token opens a new block contained by current block
        if(cur in keyword_functions):
            # get info associated with contained block
            fn = keyword_functions[cur]
            out_name = cur
            if(isinstance(fn, tuple)):
                (fn, out_name) = fn
            # process contained block
            (block_result, new_index) = fn(tokens, index + 1)
            index = new_index
            # add contained block into current block's parameters
            if(caller):
                cur_params = get_params(caller, out_name)
                cur_params += list(block_result[cur].values())
            # add contained block's results to current block's results
            for key, val in block_result.items():
                if(key in result):
                    result[key] |= val
            # some blocks have differing tokens and output names. For example, the token 'weapon', when encountered at the top level, really means 'weapon_type'
            if(not out_name in result):
                result[out_name] = {}
            result[out_name] |= block_result[out_name]
        # if current token is a parameter of current block
        elif(cur in params):
            # number of tokens in parameter
            steps = params[cur]
            index += 1
            # some parameters have multiple groups of tokens, such as weapon_effects.radius_and_pk
            if(isinstance(params[cur], tuple)):
                # list of groups of tokens in parameter
                param = []
                # create each group using the corresponding number of tokens
                for step in steps:
                    part = []
                    for i in range(0, step):
                        part.append(tokens[index])
                        index += 1
                    # make each group a string
                    param.append(" ".join(part))
            # other parameters have just one group of tokens
            else:
                part = []
                for i in range(0, steps):
                    part.append(tokens[index])
                    index += 1
                param = " ".join(part)
            # add parameter to current block
            get_params(caller, cur).append(param)
        # current token is invalid
        else:
            err(f"Illegal token '{cur}'")
            
    # return current block and the next token index to process
    return (result, index + 1)

if __name__ == "__main__":
    tokens = get_tokens("res/")
    # first pass to get all type definitions
    result = parse_all(tokens)
    types = {}
    types["platform"] = result["platform_type"]
    types["weapon"] = result["weapon_type"]
    # second pass using type definitions to fill in missing parameters
    result = parse_all(tokens)
    
    with open("out.json", "w") as f:
        f.write(json.dumps(result, sort_keys=True, indent=4))

