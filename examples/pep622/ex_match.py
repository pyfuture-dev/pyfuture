import ast

match_func = ast.parse("""
i = "name"

match i:
    case "test":
        print(i)
    case "test1":
        print(i+"123")
    # case i:
    #     print(i)
    case _:
        print(111)

""")


# TODO(gouzil): Value can be replaced with the specified type
def generate_orelse(convert_if: ast.If, subject: ast.Name, value: any, body: ast.Expr):
    if len(convert_if.orelse) == 0:
        match value:
            case ast.MatchValue:
                """
                case "test":
                """
                convert_if.orelse = [ast.If(test=ast.Compare(left=subject, ops=[ast.Is()], comparators=[value.value]), body=body, orelse=[])]
            case ast.MatchAs:
                """
                case _:
                """
                # TODO(gouzil): case [x] if x>0
                convert_if.orelse = [body]
            case _:
                RuntimeError(f"Not currently supported {value} type")
    else:
        generate_orelse(convert_if.orelse[0], subject, value, body)

for index, node in enumerate(match_func.body):
    if isinstance(node, ast.Match):
        # cache the 0th case
        zero_case = match_func.body[index].cases[0]

        """
        match value:
            case _:
        """
        if len(node.cases) == 1 and isinstance(zero_case.pattern, ast.MatchAs) and zero_case.pattern.pattern is None:
            convert_if = zero_case.body
        else:
            # Initialize `If`` Root Node
            convert_if = ast.If(test=ast.Compare(left=match_func.body[index].subject , ops=[ast.Is()], comparators=[zero_case.pattern.value]), body=zero_case.body, orelse=[])
            for case_index, case_node in enumerate(node.cases, 1):
                generate_orelse(convert_if, match_func.body[index].subject, case_node.pattern, case_node.body)
                # breakpoint()
        # print(ast.dump(convert_if))
        # breakpoint()
        match_func.body[index] = [convert_if]

print(ast.unparse(match_func))
