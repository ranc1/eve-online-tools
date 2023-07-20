import json
from typing import Optional

from models.data_models import *

TOTAL_DISPLAY_REGION = 'totalDisplayRegion'
CHILDREN = 'children'
ADDRESS = 'pythonObjectAddress'
TYPE_NAME = 'pythonObjectTypeName'
ENTRIES_OF_INTEREST = 'dictEntriesOfInterest'
NAME = '_name'
HINT = '_hint'


def parse_memory_read_to_ui_tree(file_path: str):
    with open(file_path) as f:
        ui_tree_root = json.load(f)
        ui_tree_root[TOTAL_DISPLAY_REGION] = __get_display_region(ui_tree_root)

        return __parse_ui_tree_json(ui_tree_root)


# use iteration to avoid exceeding recursion limit.
def __filter_nodes(ui_tree: dict, node_condition, parent_only: bool = True):
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


def __parse_ui_tree_json(ui_tree_root: dict) -> UiTree:
    nodes_to_check = [ui_tree_root]
    chat_window_stacks = []
    overview_window = None
    drones_window = None

    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node[TYPE_NAME] == 'ChatWindowStack':
            chat_window_stacks.append(node)
        elif node[TYPE_NAME] == 'OverviewWindow':
            overview_window = node
        elif node[TYPE_NAME] == 'DronesWindow':
            drones_window = node
        else:
            nodes_to_check.extend(__get_children_with_display_region(node))

    ui_tree = UiTree()
    ui_tree.root_address = ui_tree_root[ADDRESS]
    if chat_window_stacks:
        ui_tree.chat_windows = __parse_chat_windows(chat_window_stacks)
    if overview_window:
        ui_tree.overview = __parse_overview(overview_window)
    if drones_window:
        ui_tree.drones = __parse_drones_window(drones_window)

    return ui_tree


# Overview parsing functions start
def __parse_overview(overview_window: dict) -> list[OverviewEntry]:
    parsed_entries = []

    scroll = __filter_nodes(overview_window, lambda node: 'scroll' in node[TYPE_NAME].lower())[0]
    header = __filter_nodes(scroll, lambda node: 'headers' in node[TYPE_NAME].lower())[0]
    entries = __filter_nodes(overview_window, lambda node: node[TYPE_NAME] == 'OverviewScrollEntry')

    header_texts_nodes = __get_all_contained_text(header)

    for entry in entries:
        # parse text info.
        parsed_entry_info = {}
        for (entry_text, entry_node) in __get_all_contained_text(entry):
            entry_display_region: DisplayRegion = entry_node[TOTAL_DISPLAY_REGION]
            entry_x = entry_display_region.x
            entry_width = entry_display_region.width
            for (header_text, header_node) in header_texts_nodes:
                header_display_region: DisplayRegion = header_node[TOTAL_DISPLAY_REGION]
                header_x = header_display_region.x
                header_width = header_display_region.width

                if header_x < entry_x + 3 and header_x + header_width > entry_x + entry_width - 3:
                    parsed_entry_info[header_text] = entry_text
                    break

        indicator_texts = __parse_space_object_icon_texts(entry)
        icon_texts = __parse_right_aligned_icons(entry)

        indicators = OverviewEntryIndicators(
            locked_me='hostile' in indicator_texts,
            attacking_me='attackingMe' in indicator_texts,
            targeting='targeting' in indicator_texts,
            targeted='targetedByMeIndicator' in indicator_texts,
            is_active_target='myActiveTargetIndicator' in indicator_texts,
            neut=any('is cap neutralizing me' in text for text in icon_texts),
            tracking_disrupt=any('is tracking disrupting me' in text for text in icon_texts),
            jam=any('is jamming me' in text for text in icon_texts),
            warp_disrupt=any('is warp disrupting me' in text for text in icon_texts),
            web=any('is webifying me' in text for text in icon_texts)
        )

        parsed_entries.append(OverviewEntry(info=parsed_entry_info, indicators=indicators))
    return parsed_entries


def __parse_space_object_icon_texts(entry: dict) -> list[str]:
    """
    Parse space object icon (icon of Overview entry) as texts.
    Describes if the entry is targeting, attacking, etc.
    :param entry: Overview entry node.
    :return: Entry indicators. ie,: [hostile, attackingMe, targeting, targetedByMeIndicator, myActiveTargetIndicator]
    """
    space_object_icon = __filter_nodes(entry, lambda node: node[TYPE_NAME] == 'SpaceObjectIcon')

    if space_object_icon:
        indicator_nodes = __filter_nodes(space_object_icon[0], lambda node: '_name' in node[ENTRIES_OF_INTEREST],
                                         parent_only=False)
        return list(map(lambda node: __get_text_from_dict_entries(node, NAME), indicator_nodes))
    else:
        return []


def __parse_right_aligned_icons(entry: dict) -> list[str]:
    """
    Parse right aligned icons as lower-case texts. Describes if the entry is E-War against the user.
    :param entry: Overview entry node.
    :return: Entry indicators. ie.: [pilot is cap neutralizing me, pilot is warp disrupting me]
    """
    icon_texts = []
    right_aligned_icons = __filter_nodes(
        entry, lambda node: __get_text_from_dict_entries(node, NAME) == 'rightAlignedIconContainer')
    if right_aligned_icons:
        # Should only be at most 1 right_aligned_icons container for each entry
        icon_text_nodes = __filter_nodes(right_aligned_icons[0], lambda node: '_hint' in node[ENTRIES_OF_INTEREST])
        icon_texts.extend(list(map(lambda node: __get_text_from_dict_entries(node, HINT).lower(), icon_text_nodes)))

    return icon_texts
# Overview parsing functions end


# Chat parsing functions start
def __parse_chat_windows(chat_window_stacks: list[dict]) -> list[ChatWindow]:
    chat_window_nodes = list(map(
        lambda ui_node: __filter_nodes(ui_node, lambda node: node[TYPE_NAME] == 'XmppChatWindow')[0],
        chat_window_stacks))

    return list(map(lambda node: ChatWindow(
        name=__get_text_from_dict_entries(node, NAME),
        user_list=__parse_user_lists_from_chat(node)
    ), chat_window_nodes))


def __parse_user_lists_from_chat(chat_ui_node: dict) -> list[ChatUserEntity]:
    user_list_node = __filter_nodes(
        chat_ui_node, lambda node: 'userlist' == __get_text_from_dict_entries(node, NAME))[0]
    user_entry_nodes = __filter_nodes(
        user_list_node, lambda node: node[TYPE_NAME] in ('XmppChatSimpleUserEntry', 'XmppChatUserEntry'))

    return list(map(lambda node: ChatUserEntity(
        name=max(__get_all_contained_text(node), key=lambda node_text: len(node_text[0]))[0],
        standing=__get_standing_icon_hint(node)
    ), user_entry_nodes))


def __get_standing_icon_hint(user_entry_node: dict) -> str:
    standing_icon_node = __filter_nodes(
        user_entry_node, lambda node: node[TYPE_NAME] == 'FlagIconWithState')
    return standing_icon_node[0][ENTRIES_OF_INTEREST]['_hint'] if standing_icon_node else None
# Chat parsing functions end


# Drones parsing functions start
def __parse_drones_window(drones_window: dict) -> DroneList:
    drone_entries = __filter_nodes(
        drones_window, lambda node: node[TYPE_NAME].startswith('Drone') and node[TYPE_NAME].endswith('Entry'))

    drones = DroneList()

    for entry in drone_entries:
        entry_texts = __get_all_contained_text(entry)
        if entry_texts:
            drone = Drone(
                text=entry_texts[0][0],
                shield=__parse_drone_gauge_percentage(entry, 'shieldGauge'),
                armor=__parse_drone_gauge_percentage(entry, 'armorGauge'),
                structure=__parse_drone_gauge_percentage(entry, 'structGauge')
            )

            if 'InBay' in entry[TYPE_NAME]:
                drones.in_bay.append(drone)
            else:
                drones.in_space.append(drone)

    return drones


def __parse_drone_gauge_percentage(entry: dict, gauge_name: str) -> float:
    container = __filter_nodes(entry, lambda node: __get_text_from_dict_entries(node, NAME) == gauge_name)[0]
    gauge_bar = __filter_nodes(container, lambda node: __get_text_from_dict_entries(node, NAME) == 'droneGaugeBar')[0]
    damage_bar = __filter_nodes(
        container, lambda node: __get_text_from_dict_entries(node, NAME) == 'droneGaugeBarDmg')[0]
    hp = gauge_bar[TOTAL_DISPLAY_REGION].width
    dmg = damage_bar[TOTAL_DISPLAY_REGION].width
    return (hp - dmg) / hp * 100 if hp > 0 else 0
# Drones parsing functions end


# Utility methods
def __get_text_from_dict_entries(node: dict,  key: str) -> str:
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


def __get_children_with_display_region(parent: dict) -> list:
    parent_display_region = parent[TOTAL_DISPLAY_REGION]
    children = parent.get(CHILDREN, None)
    children_results = []

    if children:
        for child in children:
            display_region = __get_display_region(child)
            if display_region:
                display_region.x += parent_display_region.x
                display_region.y += parent_display_region.y
                child[TOTAL_DISPLAY_REGION] = display_region

                children_results.append(child)

    return children_results


def __get_display_region(node) -> Optional[DisplayRegion]:
    entries_of_interest = node[ENTRIES_OF_INTEREST]
    if all(key in entries_of_interest for key in ('_displayX', '_displayY', '_displayWidth', '_displayHeight')):
        return DisplayRegion(
            x=__get_json_int(entries_of_interest, '_displayX'),
            y=__get_json_int(entries_of_interest, '_displayY'),
            width=__get_json_int(entries_of_interest, '_displayWidth'),
            height=__get_json_int(entries_of_interest, '_displayHeight')
        )
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
