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


def parse_memory_read_to_ui_tree(file_path: str) -> UiTree:
    with open(file_path) as f:
        ui_tree_root = json.load(f)
        ui_tree_root[TOTAL_DISPLAY_REGION] = __get_display_region(ui_tree_root)

        return __parse_ui_tree_json(ui_tree_root)


def __parse_ui_tree_json(ui_tree_root: dict) -> UiTree:
    ui_tree = UiTree()
    ui_tree.root_address = ui_tree_root[ADDRESS]

    nodes_to_check = [ui_tree_root]
    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node[TYPE_NAME] == 'ChatWindowStack':
            chat_window = __parse_chat_window(node)
            if chat_window:
                ui_tree.chat_windows.append(chat_window)
        elif node[TYPE_NAME] == 'OverviewWindow':
            ui_tree.overview = __parse_overview(node)
        elif node[TYPE_NAME] == 'DronesWindow':
            ui_tree.drones = __parse_drones_window(node)
        elif node[TYPE_NAME] == 'ShipUI':
            ui_tree.ship_ui = __parse_ship_ui(node)
        else:
            nodes_to_check.extend(__get_children_with_display_region(node))

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
        entry_info = {}
        for (entry_text, entry_node) in __get_all_contained_text(entry):
            entry_display_region: DisplayRegion = entry_node[TOTAL_DISPLAY_REGION]
            entry_x = entry_display_region.x
            entry_width = entry_display_region.width
            for (header_text, header_node) in header_texts_nodes:
                header_display_region: DisplayRegion = header_node[TOTAL_DISPLAY_REGION]
                header_x = header_display_region.x
                header_width = header_display_region.width

                if header_x < entry_x + 3 and header_x + header_width > entry_x + entry_width - 3:
                    entry_info[header_text] = entry_text
                    break

        object_icon_nodes = __filter_nodes(entry, lambda node: node[TYPE_NAME] == 'SpaceObjectIcon')
        indicator_texts = __parse_space_object_icon_texts(object_icon_nodes[0]) if object_icon_nodes else []
        icon_texts = __parse_right_aligned_icons(entry)
        icon_color = __get_entry_icon_color(object_icon_nodes[0]) if object_icon_nodes else None
        icon_background_color = __get_background_color(entry)

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

        parsed_entries.append(OverviewEntry(
            info=entry_info, indicators=indicators, icon_colors=icon_color, background_colors=icon_background_color))
    return parsed_entries


def __parse_space_object_icon_texts(object_icon_node) -> list[str]:
    """
    Parse space object icon (icon of Overview entry) as texts.
    Describes if the entry is targeting, attacking, etc.
    :param object_icon_node: Space object icon node.
    :return: Entry indicators. ie,: [hostile, attackingMe, targeting, targetedByMeIndicator, myActiveTargetIndicator]
    """
    indicator_nodes = __filter_nodes(object_icon_node, lambda node: '_name' in node[ENTRIES_OF_INTEREST],
                                     parent_only=False)
    return [__get_text_from_dict_entries(node, NAME) for node in indicator_nodes]


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
        icon_texts.extend([__get_text_from_dict_entries(node, HINT).lower() for node in icon_text_nodes])

    return icon_texts


def __get_entry_icon_color(object_icon_node: dict) -> Optional[ColorPercentages]:
    sprite = __filter_nodes(object_icon_node, lambda node: __get_text_from_dict_entries(node, NAME) == 'iconSprite')
    return __get_color_from_node(sprite[0]) if sprite else None


def __get_background_color(entry: dict) -> Optional[ColorPercentages]:
    fill_nodes = __filter_nodes(entry, lambda node: node[TYPE_NAME] == 'Fill')
    bg_color_nodes = __filter_nodes(
        fill_nodes[0], lambda node: __get_text_from_dict_entries(node, NAME) == 'bgColor') if fill_nodes else None
    return __get_color_from_node(bg_color_nodes[0]) if bg_color_nodes else None
# Overview parsing functions end


# Chat parsing functions start
def __parse_chat_window(chat_window_stack: dict) -> Optional[ChatWindow]:
    chat_window_nodes = __filter_nodes(chat_window_stack, lambda node: node[TYPE_NAME] == 'XmppChatWindow')

    return ChatWindow(
        name=__get_text_from_dict_entries(chat_window_nodes[0], NAME),
        user_list=__parse_user_lists_from_chat(chat_window_nodes[0])
    ) if chat_window_nodes else None


def __parse_user_lists_from_chat(chat_ui_node: dict) -> list[ChatUserEntity]:
    user_list_nodes = __filter_nodes(
        chat_ui_node, lambda node: 'userlist' == __get_text_from_dict_entries(node, NAME))
    user_entities = []

    if user_list_nodes:
        user_list_node = user_list_nodes[0]
        user_entry_nodes = __filter_nodes(
            user_list_node, lambda node: node[TYPE_NAME] in ('XmppChatSimpleUserEntry', 'XmppChatUserEntry'))

        user_entities = []
        for user_entry_node in user_entry_nodes:
            name_texts = __get_all_contained_text(user_entry_node)
            if name_texts:
                user_entity = ChatUserEntity(
                    name=max(name_texts, key=lambda node_text: len(node_text[0]))[0],
                    standing=__get_standing_icon_hint(user_entry_node)
                )
                user_entities.append(user_entity)
                
    return user_entities


def __get_standing_icon_hint(user_entry_node: dict) -> Optional[str]:
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
            shield = __parse_drone_gauge_percentage(entry, 'shieldGauge')
            armor = __parse_drone_gauge_percentage(entry, 'armorGauge')
            structure = __parse_drone_gauge_percentage(entry, 'structGauge')
            hp_percentages = None if any(hp is None for hp in [shield, armor, structure]) else HitPointPercentages(
                shield=shield, armor=armor, structure=structure)
            drone = Drone(text=entry_texts[0][0], hp_percentages=hp_percentages)
            drones.in_bay.append(drone) if 'InBay' in entry[TYPE_NAME] else drones.in_space.append(drone)

    return drones


def __parse_drone_gauge_percentage(entry: dict, gauge_name: str) -> Optional[float]:
    containers = __filter_nodes(entry, lambda node: __get_text_from_dict_entries(node, NAME) == gauge_name)
    gauge_percentage = None
    if containers:
        gauge_bar_nodes = __filter_nodes(
            containers[0], lambda node: __get_text_from_dict_entries(node, NAME) == 'droneGaugeBar')
        damage_bar_nodes = __filter_nodes(
            containers[0], lambda node: __get_text_from_dict_entries(node, NAME) == 'droneGaugeBarDmg')
        if gauge_bar_nodes and damage_bar_nodes:
            hp = gauge_bar_nodes[0][TOTAL_DISPLAY_REGION].width
            dmg = damage_bar_nodes[0][TOTAL_DISPLAY_REGION].width
            gauge_percentage = (hp - dmg) / hp * 100 if hp > 0 else 0

    return gauge_percentage
# Drones parsing functions end


# Ship UI parsing functions start
def __parse_ship_ui(ship_ui: dict) -> ShipUI:
    return ShipUI(
        capacitor_percentage=__get_ship_capacitor(ship_ui),
        speed_text=__get_ship_speed(ship_ui),
        hp_percentages=__get_ship_hit_points(ship_ui),
        module_buttons=__parse_module_buttons(ship_ui)
    )


def __get_ship_hit_points(ship_ui: dict) -> Optional[HitPointPercentages]:
    shield = __get_last_value_from_gauge('shieldGauge', ship_ui)
    armor = __get_last_value_from_gauge('armorGauge', ship_ui)
    structure = __get_last_value_from_gauge('structureGauge', ship_ui)
    return None if any(hp is None for hp in [shield, armor, structure]) else HitPointPercentages(
        shield=shield, armor=armor, structure=structure)


def __get_ship_speed(ship_ui: dict) -> Optional[str]:
    speed_nodes = __filter_nodes(ship_ui, lambda node: node[TYPE_NAME] == 'SpeedGauge')
    speed_text = __get_all_contained_text(speed_nodes[0]) if speed_nodes else None
    return speed_text[0][0] if speed_text else None


def __get_ship_capacitor(ship_ui: dict) -> Optional[float]:
    capacitor_container_nodes = __filter_nodes(ship_ui, lambda node: node[TYPE_NAME] == 'CapacitorContainer')
    p_marks = __filter_nodes(
        capacitor_container_nodes[0],
        lambda node: __get_text_from_dict_entries(node, NAME) == 'pmark') if capacitor_container_nodes else []
    lit_p_marks = [color for color in map(__get_color_from_node, p_marks) if color and color.a < 20]
    return len(lit_p_marks) / len(p_marks) * 100 if p_marks else None


def __parse_module_buttons(ship_ui: dict) -> list[ModuleButton]:
    ship_slots = __filter_nodes(ship_ui, lambda node: node[TYPE_NAME] == 'ShipSlot')
    buttons = []
    for slot in ship_slots:
        module_button_nodes = __filter_nodes(slot, lambda node: node[TYPE_NAME] == 'ModuleButton')
        if module_button_nodes:
            module = module_button_nodes[0]
            slot_sprite = __filter_nodes(slot, lambda node: node[TYPE_NAME] == 'Sprite')

            buttons.append(ModuleButton(
                is_active=module[ENTRIES_OF_INTEREST].get('ramp_active', False),
                is_busy=any([__get_text_from_dict_entries(sprite, NAME) == 'busy' for sprite in slot_sprite]),
                display_region=module[TOTAL_DISPLAY_REGION]))

    return buttons


def __get_last_value_from_gauge(gauge_name: str, ship_ui_node: dict) -> Optional[float]:
    """
    Get the percentage value from HP gauge. If the gauge element is not present, return None. If the HP is 0, the
    '_lastValue' node will not be present, so, return 0.
    :param gauge_name: HP gauge name.
    :param ship_ui_node: Ship UI node.
    :return: HP gauge percentage value. None if the gauge is not found.
    """
    gauge_nodes = __filter_nodes(ship_ui_node, lambda node: __get_text_from_dict_entries(node, NAME) == gauge_name)
    last_value = gauge_nodes[0][ENTRIES_OF_INTEREST].get('_lastValue', 0) if gauge_nodes else None
    return last_value * 100 if type(last_value) in [int, float] else None
# Ship UI parsing functions end


# Utility methods
def __filter_nodes(ui_tree: dict, node_condition, parent_only: bool = True) -> list[dict]:
    """
    Collect the subtrees, which satisfies the node_condition, from the root ui_tree. By default, the function only
    returns the parent subtrees, then stops searching their children. When parent_only is False, the function will
    return the parent subtree, but keep searching their children.
    :param ui_tree: Root of the UI tree or subtree to start the search.
    :param node_condition: Conditions to collect the subtrees.
    :param parent_only: Whether to stop the search at the parent subtree.
    :return: List of subtrees.
    """
    nodes_to_check = [ui_tree]
    results = []

    # use iteration to avoid exceeding recursion limit.
    while nodes_to_check:
        node = nodes_to_check.pop(0)

        if node_condition(node):
            results.append(node)

            if not parent_only:
                nodes_to_check.extend(__get_children_with_display_region(node))
        else:
            nodes_to_check.extend(__get_children_with_display_region(node))

    return results


def __get_text_from_dict_entries(node: dict,  key: str) -> str:
    return node[ENTRIES_OF_INTEREST].get(key, '')


def __get_all_contained_text(root_node) -> list[(str, dict)]:
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


def __get_color_from_node(node: dict) -> Optional[ColorPercentages]:
    color = node[ENTRIES_OF_INTEREST].get('_color', None)
    return ColorPercentages(
        a=color['aPercent'], r=color['rPercent'], g=color['gPercent'], b=color['bPercent']
    ) if type(color) is dict else None


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
