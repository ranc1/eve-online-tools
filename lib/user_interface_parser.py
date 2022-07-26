import json


CHAT_WINDOW_STACK_KEY = 'chatWindowStack'


def parse_memory_read_to_ui_tree(file_path):
    with open(file_path) as f:
        return json.load(f)


def parse_chat_windows(ui_tree):
    chat_window_stacks = __filter_nodes(ui_tree, lambda node: node['pythonObjectTypeName'] == 'ChatWindowStack')
    chat_windows_nodes = list(map(
        lambda ui_node: __filter_nodes(ui_node, lambda node: node['pythonObjectTypeName'] == 'XmppChatWindow')[0],
        chat_window_stacks))

    return list(map(lambda node: {
        'name': __get_name_from_dict_entries(node),
        'userlist': __parse_user_lists_from_chat(node)
    }, chat_windows_nodes))


def get_root_memory_address(ui_tree):
    return ui_tree['pythonObjectAddress']


# use iteration to avoid exceeding recursion limit.
def __filter_nodes(ui_tree, node_condition):
    nodes_to_check = [ui_tree]
    results = []

    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node_condition(node):
            node.pop('otherDictEntriesKeys', None)
            results.append(node)
        else:
            children = node['children']
            if children:
                nodes_to_check.extend(filter(__display_region_filter, children))

    return results


def __display_region_filter(node):
    return all(key in node['dictEntriesOfInterest']
               for key in ('_displayX', '_displayY', '_displayWidth', '_displayHeight'))


def __parse_user_lists_from_chat(chat_ui_node):
    user_list_node = __filter_nodes(chat_ui_node, lambda node: 'userlist' == __get_name_from_dict_entries(node))[0]
    user_entry_nodes = __filter_nodes(
        user_list_node, lambda node: node['pythonObjectTypeName'] in ('XmppChatSimpleUserEntry', 'XmppChatUserEntry'))

    return list(map(lambda node: {
        "name": max(__get_all_contained_text(node), key=len),
        "standing": __get_standing_icon_hint(node)
    }, user_entry_nodes))


def __get_standing_icon_hint(user_entry_node):
    standing_icon_node = __filter_nodes(user_entry_node,
                                        lambda node: node['pythonObjectTypeName'] == 'FlagIconWithState')
    return standing_icon_node[0]['dictEntriesOfInterest']['_hint'] if standing_icon_node else None


def __get_name_from_dict_entries(node):
    return node['dictEntriesOfInterest'].get('_name', '')


def __get_all_contained_text(root_node):
    nodes_to_check = [root_node]
    results = []

    while nodes_to_check:
        node = nodes_to_check.pop()

        set_text_result = node['dictEntriesOfInterest'].get('_setText', None)
        text_result = node['dictEntriesOfInterest'].get('_text', None)
        if set_text_result:
            results.append(set_text_result)
        if text_result:
            results.append(text_result)

        children = node['children']
        if children:
            nodes_to_check.extend(filter(__display_region_filter, children))

    return results
