PRESETS = [
    {
        "name": "OFF",
        "displayName": "Off",
        "emoji": "✕",
        "description": "Bypass all EQ",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 0,
        "smartTunnel": False
    },
    {
        "name": "SMART",
        "displayName": "Smart",
        "emoji": "◈",
        "description": "Dynamic audio tunnel — punchy, clear, and loud without distortion",
        "bands": [150, -100, 50, 200, 100],
        "loudnessGainMb": 600,
        "smartTunnel": True
    },
    {
        "name": "ROCK",
        "displayName": "Rock",
        "emoji": "♟",
        "description": "Punchy bass, scooped mids, crisp highs",
        "bands": [500, 300, -200, 200, 400],
        "loudnessGainMb": 500,
        "smartTunnel": False
    },
    {
        "name": "JAZZ",
        "displayName": "Jazz",
        "emoji": "♫",
        "description": "Warm low-mids, airy top end",
        "bands": [300, 200, 100, 0, 200],
        "loudnessGainMb": 400,
        "smartTunnel": False
    },
    {
        "name": "CLASSIC",
        "displayName": "Classic",
        "emoji": "𝄞",
        "description": "Flat response, natural dynamics",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 300,
        "smartTunnel": False
    },
    {
        "name": "POP",
        "displayName": "Pop",
        "emoji": "♪",
        "description": "Boosted vocals & presence, tight bass",
        "bands": [-100, 200, 300, 200, 100],
        "loudnessGainMb": 400,
        "smartTunnel": False
    },
    {
        "name": "BASS",
        "displayName": "Bass",
        "emoji": "◉",
        "description": "Heavy sub & bass boost for earphones",
        "bands": [800, 600, 0, -100, -100],
        "loudnessGainMb": 600,
        "smartTunnel": False
    }
]
