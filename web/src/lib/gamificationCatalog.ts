import {
  Calendar,
  Coins,
  Crown,
  Dices,
  Flame,
  Gem,
  Share2,
  Sparkles,
  Sunrise,
  Users,
  type LucideIcon,
} from "lucide-react";

export const ACHIEVEMENT_ICONS: Record<string, LucideIcon> = {
  sunrise: Sunrise,
  flame: Flame,
  calendar: Calendar,
  users: Users,
  share: Share2,
  coins: Coins,
  gem: Gem,
  dice: Dices,
  crown: Crown,
  sparkles: Sparkles,
};

export const RATING_COLORS: Record<string, string> = {
  bronze: "#cd7f32",
  silver: "#8c9bab",
  gold: "#d4a017",
  platinum: "#5b8cff",
  diamond: "#7b61ff",
};

export const BG_STYLES: Record<string, string> = {
  default: "linear-gradient(135deg, #faf7f5 0%, #ffffff 100%)",
  aurora: "linear-gradient(135deg, #ede7ff 0%, #f5f0ff 48%, #ffffff 100%)",
  sunset: "linear-gradient(135deg, #fff1e6 0%, #ffe8cc 45%, #ffffff 100%)",
  ocean: "linear-gradient(135deg, #e6f4ff 0%, #d6ebff 50%, #ffffff 100%)",
  midnight: "linear-gradient(135deg, #1a1f36 0%, #2d3561 55%, #3d4780 100%)",
  max_gold: "linear-gradient(135deg, #3d2f14 0%, #6b5424 40%, #c9a96e 100%)",
};

export const THEME_ACCENTS: Record<string, string> = {
  default: "#c9a96e",
  ocean: "#1677ff",
  forest: "#389e0d",
  rose: "#eb2f96",
  violet: "#722ed1",
  ember: "#fa541c",
};
