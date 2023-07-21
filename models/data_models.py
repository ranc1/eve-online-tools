from dataclasses import dataclass, field


@dataclass
class HitPointsPercentages:
    shield: float = 0
    armor: float = 0
    structure: float = 0


@dataclass
class Drone:
    text: str = None
    hp_percentages: HitPointsPercentages = HitPointsPercentages


@dataclass
class DroneList:
    in_bay: list[Drone] = field(default_factory=list)
    in_space: list[Drone] = field(default_factory=list)


@dataclass
class OverviewEntryIndicators:
    locked_me: bool = False
    attacking_me: bool = False
    targeting: bool = False
    targeted: bool = False
    is_active_target: bool = False
    neut: bool = False
    tracking_disrupt: bool = False
    jam: bool = False
    warp_disrupt: bool = False
    web: bool = False


@dataclass
class OverviewEntry:
    info: dict = field(default_factory=dict)
    indicators: OverviewEntryIndicators = OverviewEntryIndicators()


@dataclass
class ChatUserEntity:
    name: str = None
    standing: str = None


@dataclass
class ChatWindow:
    name: str = None
    user_list: list[ChatUserEntity] = field(default_factory=list)


@dataclass
class ColorPercents:
    a: float = 0
    r: float = 0
    g: float = 0
    b: float = 0


@dataclass
class ShipUI:
    capacitor_percentage: float = 0
    speed_text: str = None
    hp_percentages: HitPointsPercentages = HitPointsPercentages


@dataclass
class UiTree:
    root_address: int = None
    chat_windows: list[ChatWindow] = field(default_factory=list)
    overview: list[OverviewEntry] = field(default_factory=list)
    drones: DroneList = DroneList()
    ship_ui: ShipUI = None


@dataclass
class DisplayRegion:
    x: float = None
    y: float = None
    width: float = None
    height: float = None
