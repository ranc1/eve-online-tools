import json
from typing import Optional

TOTAL_DISPLAY_REGION = 'totalDisplayRegion'
CHILDREN = 'children'
ADDRESS = 'pythonObjectAddress'
TYPE_NAME = 'pythonObjectTypeName'
ENTRIES_OF_INTEREST = 'dictEntriesOfInterest'
NAME = '_name'
HINT = '_hint'

ENTRY_INDICATORS = 'indicators'


class UiTree:
    def __init__(self):
        self.root_address = None
        self.chat_windows = None
        self.overview = None


def parse_memory_read_to_ui_tree(file_path):
    with open(file_path) as f:
        ui_tree_root = json.load(f)
        ui_tree_root[TOTAL_DISPLAY_REGION] = __get_display_region(ui_tree_root)

        return __parse_ui_tree_json(ui_tree_root)


# use iteration to avoid exceeding recursion limit.
def __filter_nodes(ui_tree, node_condition, parent_only=True):
    nodes_to_check = [ui_tree]
    results = []

    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node_condition(node):
            results.append(node)

            if not parent_only:
                nodes_to_check.extend(__get_children_with_display_region(node))
        else:
            nodes_to_check.extend(__get_children_with_display_region(node))

    return results


def __parse_ui_tree_json(ui_tree_root) -> UiTree:
    nodes_to_check = [ui_tree_root]
    chat_window_stacks = []
    overview_window = None

    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node[TYPE_NAME] == 'ChatWindowStack':
            chat_window_stacks.append(node)
        elif node[TYPE_NAME] == 'OverviewWindow':
            overview_window = node
        else:
            nodes_to_check.extend(__get_children_with_display_region(node))

    ui_tree = UiTree()
    ui_tree.root_address = ui_tree_root[ADDRESS]
    if chat_window_stacks:
        ui_tree.chat_windows = __parse_chat_windows(chat_window_stacks)
    if overview_window:
        ui_tree.overview = __parse_overview(overview_window)

    return ui_tree


def __parse_overview(overview_window) -> list[dict]:
    parsed_entries = []

    scroll = __filter_nodes(overview_window, lambda node: 'scroll' in node[TYPE_NAME].lower())[0]
    header = __filter_nodes(scroll, lambda node: 'headers' in node[TYPE_NAME].lower())[0]
    entries = __filter_nodes(overview_window, lambda node: node[TYPE_NAME] == 'OverviewScrollEntry')

    header_texts_nodes = __get_all_contained_text(header)

    for entry in entries:
        # parse text info.
        parsed_entry = {}
        for (entry_text, entry_node) in __get_all_contained_text(entry):
            entry_display_region = entry_node[TOTAL_DISPLAY_REGION]
            entry_x = entry_display_region['x']
            entry_width = entry_display_region['width']
            for (header_text, header_node) in header_texts_nodes:
                header_display_region = header_node[TOTAL_DISPLAY_REGION]
                header_x = header_display_region['x']
                header_width = header_display_region['width']

                if header_x < entry_x + 3 and header_x + header_width > entry_x + entry_width - 3:
                    parsed_entry[header_text] = entry_text
                    break

        # parse icon indicators
        space_object_icon = __filter_nodes(entry, lambda node: node[TYPE_NAME] == 'SpaceObjectIcon')[0]
        indicator_nodes = __filter_nodes(space_object_icon, lambda node: '_name' in node[ENTRIES_OF_INTEREST],
                                         parent_only=False)
        indicator_texts = list(map(lambda node: __get_text_from_dict_entries(node, NAME), indicator_nodes))

        # parse right aligned icons
        icon_texts = []
        right_aligned_icons = __filter_nodes(
            entry, lambda node: __get_text_from_dict_entries(node, NAME) == 'rightAlignedIconContainer')
        if right_aligned_icons:
            # Should only be at most 1 right_aligned_icons container for each entry
            icon_text_nodes = __filter_nodes(right_aligned_icons[0], lambda node: '_hint' in node[ENTRIES_OF_INTEREST])
            icon_texts.extend(list(map(lambda node: __get_text_from_dict_entries(node, HINT).lower(), icon_text_nodes)))

        indicators = {
            'lockedMe': 'hostile' in indicator_texts,
            'attackingMe': 'attackingMe' in indicator_texts,
            'targeting': 'targeting' in indicator_texts,
            'targetedByMe': 'targetedByMeIndicator' in indicator_texts,
            'isActiveTarget': 'myActiveTargetIndicator' in indicator_texts,
            'neut': any('is cap neutralizing me' in text for text in icon_texts),
            'trackingDisrupt': any('is tracking disrupting me' in text for text in icon_texts),
            'jam': any('is jamming me' in text for text in icon_texts),
            'warpDisrupt': any('is warp disrupting me' in text for text in icon_texts)
        }
        parsed_entry[ENTRY_INDICATORS] = indicators

        parsed_entries.append(parsed_entry)
    return parsed_entries


def __parse_chat_windows(chat_window_stacks):
    chat_window_nodes = list(map(
        lambda ui_node: __filter_nodes(ui_node, lambda node: node[TYPE_NAME] == 'XmppChatWindow')[0],
        chat_window_stacks))

    return list(map(lambda node: {
        'name': __get_text_from_dict_entries(node, NAME),
        'userlist': __parse_user_lists_from_chat(node)
    }, chat_window_nodes))


def __display_region_filter(node):
    return all(key in node[ENTRIES_OF_INTEREST]
               for key in ('_displayX', '_displayY', '_displayWidth', '_displayHeight'))


def __parse_user_lists_from_chat(chat_ui_node):
    user_list_node = __filter_nodes(
        chat_ui_node, lambda node: 'userlist' == __get_text_from_dict_entries(node, NAME))[0]
    user_entry_nodes = __filter_nodes(
        user_list_node, lambda node: node[TYPE_NAME] in ('XmppChatSimpleUserEntry', 'XmppChatUserEntry'))

    return list(map(lambda node: {
        "name": max(__get_all_contained_text(node), key=lambda node_text: len(node_text[0]))[0],
        "standing": __get_standing_icon_hint(node)
    }, user_entry_nodes))


def __get_standing_icon_hint(user_entry_node):
    standing_icon_node = __filter_nodes(
        user_entry_node, lambda node: node[TYPE_NAME] == 'FlagIconWithState')
    return standing_icon_node[0][ENTRIES_OF_INTEREST]['_hint'] if standing_icon_node else None


def __get_text_from_dict_entries(node,  key):
    return node[ENTRIES_OF_INTEREST].get(key, '')


def __get_all_contained_text(root_node) -> [(str, dict)]:
    """
    Parse contained texts as a list from root_node and its children.
    :param root_node: Root
    :return: List of (text, node) tuples.
    """
    results = []

    nodes_with_text = __filter_nodes(
        root_node, lambda n: any(key in n[ENTRIES_OF_INTEREST] for key in ['_setText', '_text']), parent_only=False)
    for node in nodes_with_text:
        entries_of_interest = node[ENTRIES_OF_INTEREST]
        text = max([entries_of_interest.get('_setText', ''), entries_of_interest.get('_text', '')], key=len)
        results.append((text, node))

    return results


def __get_children_with_display_region(parent) -> list:
    parent_display_region = parent[TOTAL_DISPLAY_REGION]
    children = parent.get(CHILDREN, None)
    children_results = []

    if children:
        for child in children:
            display_region = __get_display_region(child)
            if display_region:
                display_region['x'] += parent_display_region['x']
                display_region['y'] += parent_display_region['y']
                child[TOTAL_DISPLAY_REGION] = display_region
                child.pop('otherDictEntriesKeys', None)

                children_results.append(child)

    return children_results


def __get_display_region(node) -> Optional[dict[str, float]]:
    entries_of_interest = node[ENTRIES_OF_INTEREST]
    if all(key in entries_of_interest for key in ('_displayX', '_displayY', '_displayWidth', '_displayHeight')):
        return {
            'x': __get_json_int(entries_of_interest, '_displayX'),
            'y': __get_json_int(entries_of_interest, '_displayY'),
            'width': __get_json_int(entries_of_interest, '_displayWidth'),
            'height': __get_json_int(entries_of_interest, '_displayHeight')
        }
    else:
        return None


def __get_json_int(node, key) -> float:
    value = node[key]
    if isinstance(value, int) or isinstance(value, float):
        return value
    elif 'int_low32' in value:
        return value['int_low32']
    else:
        return 0
