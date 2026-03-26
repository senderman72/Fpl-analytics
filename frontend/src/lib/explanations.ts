/** Plain English explanations for every stat shown in the app. */

export const STAT_HELP: Record<string, string> = {
  xgi_per_90:
    "Expected Goal Involvement per 90 minutes played. Combines expected goals (xG) and expected assists (xA) to measure attacking output. Higher = more likely to score or assist. Based on shot/chance quality data from Understat.",
  bps:
    "Bonus Point System — FPL's hidden scoring system. Every action in a match earns or loses BPS points. The top 3 players in each match receive 3, 2, and 1 bonus FPL points.",
  bps_avg:
    "Average BPS score per game started over the last 6 gameweeks. Consistently high BPS (25+) means a player regularly picks up bonus points.",
  ict:
    "Influence, Creativity, Threat — FPL's index measuring overall match impact. Influence = defensive actions, Creativity = chance creation, Threat = goal-scoring danger.",
  ppm:
    "Points Per Million — form points divided by price. A player at £6.0m scoring 30 points = 5.0 PPM. Higher PPM = better value for your budget.",
  fdr:
    "Fixture Difficulty Rating (1-5 scale). 1-2 (green) = easy opponents. 3 (grey) = average. 4-5 (red) = tough opponents. Based on FPL's team strength ratings.",
  ceiling:
    "Highest single-gameweek score in the last 10 appearances. Shows explosive potential — important for captaincy as you want upside, not just consistency.",
  form:
    "Total FPL points scored in the last 6 gameweeks. Quick measure of who's hot right now. A good form score depends on position — 25+ is strong for any player.",
  minutes_pct:
    "Percentage of available minutes played recently. 80%+ = nailed-on starter. 50-80% = rotation risk. Below 50% = bench player or recently returned from injury.",
  ownership:
    "Percentage of all FPL managers who own this player. High ownership (30%+) = template pick everyone has. Low ownership (<5%) = differential that can help you climb the ranks.",
  npxg:
    "Non-Penalty Expected Goals — xG excluding penalties. Shows a player's open-play goal threat. Useful for comparing attackers without the noise of penalty duties.",
  xg:
    "Expected Goals — the quality of chances a player has had, measured by the probability of scoring from each shot. If a player has 10 xG but 15 goals, they're overperforming.",
  xa:
    "Expected Assists — the quality of chances a player creates for teammates. Measures creativity independent of whether the teammate finishes the chance.",
  dgw:
    "Double Gameweek — a team plays TWO matches in one gameweek. Players can earn points from both games, making them premium captain and Bench Boost targets.",
  bgw:
    "Blank Gameweek — a team has NO match this gameweek. Their players score 0 points. Use the Free Hit chip to temporarily swap them out.",
  transfers_in:
    "Number of FPL managers who transferred this player IN this gameweek. High numbers (50k+) = very popular pick, possible price rise coming.",
  transfers_out:
    "Number of FPL managers who transferred this player OUT this gameweek. High numbers = managers losing faith, possible price drop.",
  price_change:
    "Price change since the gameweek started. +0.1 = price rose by £0.1m. Prices change overnight based on transfer activity.",
  pts_per_game:
    "Average FPL points per game started over the last 6 gameweeks. Accounts for blanks and big hauls. 5+ per game is a strong return.",
};
