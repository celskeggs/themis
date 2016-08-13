import themis.cgen.templates

_opt_passes = []

wildcard = object()
CALLBACK_ELIM = ["start_timer_ns"]


def tree_match(tree, template):
    if template is wildcard:
        return True
    elif type(tree) != type(template):
        return False
    elif tree == template:
        return True
    elif type(tree) != tuple:
        return False
    elif len(tree) != len(template):
        return False
    else:
        return all(tree_match(subtree, subtemplate) for subtree, subtemplate in zip(tree, template))


def tree_replace(tree, template_list, substitutor, replace_before=False):
    if any(tree_match(tree, template) for template in template_list):
        if replace_before and type(tree) == tuple:
            tree = (tree[0],) + tuple(
                tree_replace(subtree, template_list, substitutor, replace_before) for subtree in tree[1:])
        return substitutor(tree)
    elif type(tree) == tuple:
        return (tree[0],) + tuple(
            tree_replace(subtree, template_list, substitutor, replace_before) for subtree in tree[1:])
    elif type(tree) == list:
        return tree_replace_all(tree, template_list, substitutor, replace_before)
    else:
        return tree


def tree_replace_all(trees, template_list, substitutor, replace_before=False):
    return [tree_replace(tree, template_list, substitutor, replace_before) for tree in trees]


def replace_in_instants(instants, template_list, substitutor, replace_before=False):
    for instant in instants:
        instant._body = tree_replace_all(instant._body, template_list, substitutor, replace_before)


def tree_walk(tree, walker):
    has_changed = False
    if type(tree) == list or type(tree) == tuple:
        out = None
        for i in range(len(tree)):
            change, value = tree_walk(tree[i], walker)
            if change:
                if out is None:
                    out = tree[:]
                out[i] = value
        has_changed = out is not None
        if has_changed:
            tree = tuple(out) if type(tree) == tuple else out
    change, value = walker(tree)
    if change:
        return True, value
    else:
        return has_changed, tree


def replace_walk_in_instants(instants, walker):
    for instant in instants:
        update, value = tree_walk(instant._body, walker)
        if update:
            instant._body = value


def tree_walk_ro(tree, walker):
    if type(tree) == list or type(tree) == tuple:
        for subtree in tree:
            tree_walk_ro(subtree, walker)
    walker(tree)


def opt_pass(op):
    _opt_passes.append(op)


@opt_pass
def opt_eliminate_empty(root_instant, instants: set):
    to_remove = [instant for instant in instants if instant.is_empty() and instant is not root_instant]
    if not to_remove:
        return root_instant, instants
    instants.difference_update(to_remove)

    # === ELIMINATE DIRECT CALLS ===
    def substitutor(tree):
        assert tree[0] in (
            themis.cgen.templates.invoke_nullary, themis.cgen.templates.invoke_unary,
            themis.cgen.templates.invoke_poly)
        assert tree[1] in to_remove
        return (themis.cgen.templates.nop,)

    template_list = []
    for instant in to_remove:
        template_list += [(themis.cgen.templates.invoke_nullary, instant),
                          (themis.cgen.templates.invoke_unary, instant, wildcard),
                          (themis.cgen.templates.invoke_poly, instant, wildcard)]
    replace_in_instants(instants, template_list, substitutor)

    # === ELIMINATE INDIRECT USES ===
    def substitutor_2(tree):
        if tree[0] == themis.cgen.templates.invoke_unary and tree[2] in to_remove:
            if tree[1] in CALLBACK_ELIM:
                return (themis.cgen.templates.nop,)
            else:
                return tree[0:2] + ("do_nothing",) + tree[3:]
        else:
            assert tree[0] == themis.cgen.templates.invoke_poly
            if any(elem in to_remove for elem in tree[2]):
                if tree[1] in CALLBACK_ELIM:
                    return (themis.cgen.templates.nop,)
                else:
                    updated_args = [(arg if arg not in to_remove else "do_nothing") for arg in tree[2]]
                    return tree[0:2] + (updated_args,) + tree[3:]
            else:
                return tree

    template_list = [(themis.cgen.templates.invoke_poly, wildcard, wildcard)]
    for instant in to_remove:
        template_list += [(themis.cgen.templates.invoke_unary, wildcard, instant)]
    replace_in_instants(instants, template_list, substitutor_2, replace_before=True)

    return root_instant, instants


@opt_pass
def opt_eliminate_nops(root_instant, instants):
    def walker(tree):
        if type(tree) == list and (themis.cgen.templates.nop,) in tree:
            return True, [elem for elem in tree if elem != (themis.cgen.templates.nop,)]
        return False, None

    replace_walk_in_instants(instants, walker)
    return root_instant, instants


def check_get_simple_call(instant):
    if len(instant._body) != 1: return
    if instant._param_type is None:
        if instant._body[0][0] == themis.cgen.templates.invoke_nullary \
                and isinstance(instant._body[0][1], themis.cgen.Instant):
            return instant._body[0][1]
    else:
        if instant._body[0][0] == themis.cgen.templates.invoke_unary \
                and isinstance(instant._body[0][1], themis.cgen.Instant) and instant._body[0][2] == instant._param:
            return instant._body[0][1]


@opt_pass
def opt_inline_simple(root_instant, instants: set):
    remaps = {}
    for instant in instants:
        simple_target = check_get_simple_call(instant)
        if simple_target is not None:
            remaps[instant] = simple_target
    # === ELIMINATE REMAPPED INSTANTS FROM INSTANT LIST ===
    instants.difference_update(remaps.keys())

    # === REMAP USES OF REMOVED INSTANTS ===
    def substitutor(tree):
        assert tree in remaps
        while tree in remaps:  # TODO: notice infinite loops
            tree = remaps[tree]
        return tree

    replace_in_instants(instants, [instant for instant in remaps.keys()], substitutor, replace_before=True)
    return root_instant, instants


def calculate_refcounts(root_instant, instants):
    refs = {instant: [] for instant in instants}
    refs[root_instant].append(None)

    for instant in instants:
        def walker(tree):
            if isinstance(tree, themis.cgen.Instant):
                refs[tree].append(instant)

        tree_walk_ro(instant._body, walker)

    return refs


def get_modified_variables(instant):
    refed = {instant._param} if instant._param_type is not None else set()

    def walker(tree):
        if type(tree) == tuple and tree[0] == themis.cgen.templates.set:
            refed.add(tree[1])

    tree_walk_ro(instant._body, walker)

    return refed


@opt_pass
def opt_inline(root_instant, instants: set):
    refs = calculate_refcounts(root_instant, instants)
    inlineable = [instant for instant, ref in refs.items() if len(ref) == 1 and instant is not root_instant]
    inlineable.sort(key=lambda x: x._uid)
    actually_inlined = []
    for instant in inlineable:
        refed_in = refs[instant][0]
        while refed_in in actually_inlined:
            refed_in = refs[refed_in][0]
        assert refed_in is not instant
        if get_modified_variables(refed_in).intersection(get_modified_variables(instant)):
            print("VARDUP BYPASS", instant._instant, "INTO", refed_in._instant)
            continue
        found_line = [i for i, line in enumerate(refed_in._body)
                      if line[0] in (themis.cgen.templates.invoke_nullary, themis.cgen.templates.invoke_unary)
                      and line[1] == instant]
        if not found_line:
            continue
        assert len(found_line) == 1
        line_id = found_line[0]
        if refed_in._body[line_id][0] == themis.cgen.templates.invoke_nullary:
            assert instant._param_type is None
            refed_in._body[line_id:line_id + 1] = instant._body
        else:
            assert instant._param_type is not None
            refed_in._body[line_id:line_id + 1] = [(themis.cgen.templates.set_decl,
                                                    themis.cgen.PARAM_TYPES[instant._param_type], instant._param,
                                                    refed_in._body[line_id][2])] + instant._body
        actually_inlined.append(instant)

    instants.difference_update(actually_inlined)
    return root_instant, instants


def optimize(root_instant, instants):
    for op in _opt_passes:
        root_instant, instants = op(root_instant, instants)

    return root_instant, instants
