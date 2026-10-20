"""Rangers sticker flair definitions: Jersey numbers, positions, stats formatting and badge HTML."""

# Jersey numbers for New York Rangers target and legendary players
JERSEY_NUMBERS = {
    # 1994 Stanley Cup Champions
    8449573: 11,  # Mark Messier
    8448769: 2,   # Brian Leetch
    8447363: 9,   # Adam Graves
    8450725: 35,  # Mike Richter
    8452589: 56,  # Sergei Zubov
    8458951: 27,  # Alexei Kovalev
    8448695: 17,  # Steve Larmer
    8451834: 10,  # Esa Tikkanen
    8457245: 32,  # Stephane Matteau
    8444945: 36,  # Glenn Anderson
    8448962: 14,  # Craig MacTavish
    8445461: 23,  # Jeff Beukeboom
    8448899: 4,   # Kevin Lowe
    8452378: 6,   # Jay Wells
    8457519: 26,  # Brian Noonan
    8447171: 15,  # Greg Gilbert
    8457500: 13,  # Sergei Nemchinov
    8457004: 18,  # Nick Kypreos
    8448509: 25,  # Joey Kocur
    8448068: 21,  # Mike Hudson
    8448831: 24,  # Doug Lidster
    8450005: 12,  # Ed Olczyk
    8447667: 30,  # Glenn Healy
    8456795: 38,  # Alexander Karpovtsev
    8455375: 33,  # Peter Anderson
    8447629: 22,  # Mike Hartman
    8449572: 29,  # Joby Messier
    8449646: 16,  # Corey Millen
    8459461: 15,  # Todd Marchant
    8456950: 28,  # Daniel Lacroix
    8459021: 14,  # Mattias Norstrom
    8445620: 29,  # Phil Bourque
    8450218: 4,   # James Patrick
    8455986: 28,  # Mike Eastwood
    8451996: 10,  # Darren Turcotte
    8445037: 17,  # Tony Amonte
    8444914: 15,  # Mike Allison
    8451559: 5,   # Steve Smith

    # Current 2024-2026 Roster
    8481726: 84,  # Adam Edstrom
    8479323: 23,  # Adam Fox
    8483669: 38,  # Adam Sykora
    8485957: 37,  # Alberts Smits
    8482109: 13,  # Alexis Lafreniere
    8477320: 81,  # Anton Blidh
    8478550: 10,  # Artemi Panarin
    8481560: 34,  # Arthur Kaliyev
    8482073: 4,   # Braden Schneider
    8482153: 19,  # Brendan Brisson
    8482747: 78,  # Brennan Othmann
    8482132: 65,  # Brett Berard
    8475177: 44,  # Calvin de Haan
    8477369: 7,   # Carson Soucy
    8477244: 5,   # Chad Ruhwedel
    8475184: 20,  # Chris Kreider
    8484786: 25,  # Cole Beaudoin
    8482067: 29,  # Connor Mackey
    8477839: 43,  # Conor Sheary
    8484169: 36,  # Drew Fortescue
    8482193: 30,  # Dylan Garand
    8480009: 28,  # Eeli Tolvanen
    8480078: 72,  # Filip Chytil
    8484210: 86,  # Gabe Perreault
    8478048: 31,  # Igor Shesterkin
    8476468: 10,  # J.T. Miller
    8476885: 8,   # Jacob Trouba
    8482877: 81,  # Jaroslav Chmelar
    8476918: 26,  # Jimmy Vesey
    8471734: 32,  # Jonathan Quick
    8477380: 22,  # Jonny Brodzinski
    8480813: 90,  # Joseph Veleno
    8475413: 51,  # Justin Dowling
    8481704: 75,  # Juuso Parssinen
    8480817: 79,  # K'Andre Miller
    8481554: 24,  # Kaapo Kakko
    8475839: 70,  # Louis Domingue
    8477969: 28,  # Marcus Pettersson
    8482460: 73,  # Matt Rempe
    8481525: 44,  # Matthew Robertson
    8476459: 93,  # Mika Zibanejad
    8477979: 96,  # Nicolas Aube-Kubel
    8483690: 19,  # Noah Laba
    8477416: 22,  # Oliver Bjorkstrand
    8481604: 14,  # Pavel Dorofeyev
    8475191: 22,  # Reilly Smith
    8479324: 55,  # Ryan Lindgren
    8475842: 39,  # Sam Carrick
    8482666: 28,  # Scott Morrow
    8480434: 64,  # Sean Durzi
    8477484: 33,  # Spencer Martin
    8479390: 17,  # Taylor Raddysh
    8481789: 52,  # Tye Kartye
    8480001: 58,  # Urho Vaakanainen
    8483768: 90,  # Victor Mancini
    8482861: 2,   # Vincent Iorio
    8476389: 16,  # Vincent Trocheck
    8478882: 44,  # Vladislav Gavrikov
    8482157: 50,  # Will Cuylle
    8478840: 3,   # William Borgen
    8481708: 6,   # Zac Jones

    # 1940 Stanley Cup Champions
    8445582: 5,   # Neil Colville
    8445581: 7,   # Mac Colville
    8446853: 12,  # Bryan Hextall
    8449377: 11,  # Phil Watson
    8448102: 8,   # Lynn Patrick
    8448103: 6,   # Muzz Patrick
    8448163: 14,  # Alf Pike
    8450004: 1,   # Dave Kerr
    8445722: 3,   # Art Coulter
    8448183: 2,   # Babe Pratt
    8447558: 10,  # Kilby MacDonald
    8446867: 16,  # Dutch Hiller
    8449089: 15,  # Clint Smith
    8448995: 9,   # Alex Shibicky
    8446816: 4,   # Ott Heller
    8449102: 17,  # Stanford Smith
    8444871: 18,  # George Allen
    8445529: 3,   # Jack Church

    # 1933 Stanley Cup Champions
    8445695: 5,   # Bill Cook
    8445696: 6,   # Bun Cook
    8445136: 7,   # Frank Boucher
    8447055: 2,   # Ching Johnson
    8447913: 14,  # Murray Murdoch
    8445903: 9,   # Cecil Dillon
    8448987: 3,   # Babe Siebert
    8444869: 1,   # Andy Aitkenhead
    8445279: 4,   # Doug Brennan
    8448151: 10,  # Gord Pettinger
    8444982: 11,  # Ossie Asmundson
    8447190: 8,   # Butch Keeling
    8449114: 12,  # Art Somers
    8446497: 15,  # Percy Galbraith

    # 1928 Stanley Cup Champions
    8444855: 4,   # Taffy Abel
    8449850: 1,   # Lorne Chabot
    8449237: 11,  # Paul Thompson
    8445218: 3,   # Leo Bourgeault
    8446639: 8,   # Alex Gray
    8450043: 1,   # Joe Miller
    8445274: 9,   # Billy Boyd
    8445499: 12,  # Frank Callighen
    8448949: 15,  # Laurie Scott
    8449007: 16,  # Stan Sislo

    # Other Legendary / Retired Rangers
    8447400: 99,  # Wayne Gretzky
    8468685: 30,  # Henrik Lundqvist
    8446580: 7,   # Rod Gilbert
    8449987: 1,   # Ed Giacomin
    8448259: 19,  # Jean Ratelle
    8446658: 11,  # Vic Hadfield
    8445032: 9,   # Andy Bathgate
    8447000: 3,   # Harry Howell
}

POSITION_NAMES = {
    'C': 'Center',
    'D': 'Defenseman',
    'G': 'Goaltender',
    'L': 'Left Wing',
    'LW': 'Left Wing',
    'R': 'Right Wing',
    'RW': 'Right Wing',
    'F': 'Forward',
}


def get_jersey_number(player_id: int) -> int | None:
    """Return official NY Rangers jersey number, or None if unlisted."""
    return JERSEY_NUMBERS.get(int(player_id))


def get_position_display(positions: list[str]) -> str:
    """Format position codes into user-friendly names."""
    if not positions:
        return "Skater"
    expanded = [POSITION_NAMES.get(p, p) for p in positions]
    return " / ".join(expanded)


def get_primary_position_code(positions: list[str]) -> str:
    """Return primary short code for badge pills: C, LW, RW, D, G."""
    if not positions:
        return "F"
    pos = positions[0]
    if pos == 'L': return 'LW'
    if pos == 'R': return 'RW'
    return pos


def format_stats_ribbon(player: dict) -> str:
    """Build compact stats pill ribbon for card flair."""
    stats = player.get("stats", {}).get("regular_season", {})
    if "skater" in stats:
        s = stats["skater"]
        gp = s.get("gamesPlayed", 0) or 0
        g = s.get("goals", 0) or 0
        a = s.get("assists", 0) or 0
        pts = s.get("points", 0) or 0
        return (
            '<div class="stats-ribbon skater-stats">'
            f'<div class="stat-col"><span class="stat-num">{gp}</span><span class="stat-lbl">GP</span></div>'
            f'<div class="stat-col"><span class="stat-num">{g}</span><span class="stat-lbl">G</span></div>'
            f'<div class="stat-col"><span class="stat-num">{a}</span><span class="stat-lbl">A</span></div>'
            f'<div class="stat-col stat-highlight"><span class="stat-num">{pts}</span><span class="stat-lbl">PTS</span></div>'
            '</div>'
        )
    elif "goalie" in stats:
        g = stats["goalie"]
        gp = g.get("gamesPlayed", 0) or 0
        w = g.get("wins", 0) or 0
        so = g.get("shutouts", 0) or 0
        sv_pct = g.get("savePct")
        sv_str = f"{sv_pct:.3f}".lstrip("0") if sv_pct is not None else "--"
        gaa = g.get("goalsAgainstAverage")
        gaa_str = f"{gaa:.2f}" if gaa is not None else "--"
        return (
            '<div class="stats-ribbon goalie-stats">'
            f'<div class="stat-col"><span class="stat-num">{gp}</span><span class="stat-lbl">GP</span></div>'
            f'<div class="stat-col"><span class="stat-num">{w}</span><span class="stat-lbl">W</span></div>'
            f'<div class="stat-col"><span class="stat-num">{sv_str}</span><span class="stat-lbl">SV%</span></div>'
            f'<div class="stat-col stat-highlight"><span class="stat-num">{gaa_str}</span><span class="stat-lbl">GAA</span></div>'
            '</div>'
        )
    # Check playoff-only stats
    playoffs = player.get("stats", {}).get("playoffs", {})
    if "skater" in playoffs:
        s = playoffs["skater"]
        return f'<div class="stats-ribbon playoff-stats"><span class="stat-num">{s.get("gamesPlayed",0)} Playoff GP · {s.get("points",0)} PTS</span></div>'
    elif "goalie" in playoffs:
        g = playoffs["goalie"]
        return f'<div class="stats-ribbon playoff-stats"><span class="stat-num">{g.get("gamesPlayed",0)} Playoff GP · {g.get("wins",0)} W</span></div>'
    return ""


def get_image_flair_html(player: dict, level: int = 1) -> str:
    """Render authentic stitched jersey patch overlay directly on top of the image container."""
    pid = player.get("player_id")
    num = get_jersey_number(pid) if pid else None
    pos_code = get_primary_position_code(player.get("positions", []))

    num_html = f'<div class="jersey-patch level-{level}">#{num}</div>' if num is not None else ''
    pos_html = f'<div class="pos-patch level-{level}">{pos_code}</div>'

    return f'<div class="card-image-flair">{num_html}{pos_html}</div>'
