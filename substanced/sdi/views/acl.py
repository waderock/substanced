import re

from pyramid.security import (
    Deny,
    Everyone,
    AllPermissionsList,
    )

from substanced.interfaces import ICatalogable

from substanced.catalog import find_catalog

from substanced.subscribers import (
    _postorder as postorder,
    )

from substanced.sdi import mgmt_view

def get_workflow(*arg, **kw):
    return

def get_security_states(*arg, **kw):
    return []

COMMA_WS = re.compile(r'[\s,]+')

ALL = AllPermissionsList()
NO_INHERIT = (Deny, Everyone, ALL)

def get_context_workflow(context):
    """
    If context is content and part of a workflow will return the workflow.
    Otherwise returns None.
    """
    return

@mgmt_view(name='security', permission='change security', 
           renderer='templates/acl_edit.pt', tab_title='Security')
def acl_edit_view(context, request):

    acl = original_acl = getattr(context, '__acl__', [])
    if acl and acl[-1] == NO_INHERIT:
        acl = acl[:-1]
        epilog = [NO_INHERIT]
    else:
        epilog = []

    if 'form.move_up' in request.POST:
        index = int(request.POST['index'])
        if index > 0:
            new = acl[:]
            new[index-1], new[index] = new[index], new[index-1]
            acl = new

    elif 'form.move_down' in request.POST:
        index = int(request.POST['index'])
        if index < len(acl) - 1:
            new = acl[:]
            new[index+1], new[index] = new[index], new[index+1]
            acl = new

    elif 'form.remove' in request.POST:
        index = int(request.POST['index'])
        new = acl[:]
        del new[index]
        acl = new

    elif 'form.add' in request.POST:
        verb = request.POST['verb']
        principal = request.POST['principal']
        permissions = tuple(filter(None,
                              COMMA_WS.split(request.POST['permissions'])))
        new = acl[:]
        new.append((verb, principal, permissions))
        acl = new

    elif 'form.inherit' in request.POST:
        no_inherit = request.POST['inherit'] == 'disabled'
        if no_inherit:
            epilog = [NO_INHERIT]
        else:
            epilog = []

    elif 'form.security_state' in request.POST:
        new_state = request.POST['security_state']
        if new_state != 'CUSTOM':
            workflow = get_context_workflow(context)
            if hasattr(context, '__custom_acl__'):
                workflow.reset(context)
                del context.__custom_acl__
            workflow.transition_to_state(context, request, new_state)

    acl = acl + epilog

    if acl != original_acl:
        context.__custom_acl__ = acl # added so we can find customized obs later
        context.__acl__ = acl
        catalog = find_catalog(context)
        if catalog is not None:
            allowed = catalog.get('allowed')
            if allowed is not None:
                for node in postorder(context):
                    if ICatalogable.providedBy(node):
                        catalog.reindex_doc(node.__objectid__, node)

    workflow = get_context_workflow(context)
    if workflow is not None:
        if hasattr(context, '__custom_acl__'):
            security_state = 'CUSTOM'
            security_states = [s['name'] for s in
                               workflow.state_info(context, request)]
            security_states.insert(0, 'CUSTOM')
        else:
            security_state = workflow.state_of(context)
            security_states = [s['name'] for s in
                               get_security_states(workflow, context, request)]

    else:
        security_state = None
        security_states = None

    parent = context.__parent__
    parent_acl = []
    while parent is not None:
        p_acl = getattr(parent, '__acl__', ())
        stop = False
        for ace in p_acl:
            if ace == NO_INHERIT:
                stop = True
            else:
                parent_acl.append(ace)
        if stop:
            break
        parent = parent.__parent__

    local_acl = []
    inheriting = 'enabled'
    l_acl = getattr(context, '__acl__', ())
    for l_ace in l_acl:
        if l_ace == NO_INHERIT:
            inheriting = 'disabled'
            break
        local_acl.append(l_ace)


    return dict(
        parent_acl=parent_acl or (),
        local_acl=local_acl,
        inheriting=inheriting,
        security_state=security_state,
        security_states=security_states)

