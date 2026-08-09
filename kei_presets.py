PRESETS = [
    {
        "name": "OFF",
        "displayName": "Off",
        "emoji": "✕",
        "description": "Bypass all EQ",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 0,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "SMART",
        "displayName": "Smart",
        "emoji": "◈",
        "description": "Dynamic audio tunnel — punchy, clear, and loud without distortion",
        "bands": [150, -100, 50, 200, 100],
        "loudnessGainMb": 600,
        "smartTunnel": True,
        "spatialAudio": True
    },
    {
        "name": "ROCK",
        "displayName": "Rock",
        "emoji": "♟",
        "description": "Punchy bass, scooped mids, crisp highs",
        "bands": [500, 300, -200, 200, 400],
        "loudnessGainMb": 500,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "JAZZ",
        "displayName": "Jazz",
        "emoji": "♫",
        "description": "Warm low-mids, airy top end",
        "bands": [300, 200, 100, 0, 200],
        "loudnessGainMb": 400,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "CLASSIC",
        "displayName": "Classic",
        "emoji": "𝄞",
        "description": "Flat response, natural dynamics",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 300,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "POP",
        "displayName": "Pop",
        "emoji": "♪",
        "description": "Boosted vocals & presence, tight bass",
        "bands": [-100, 200, 300, 200, 100],
        "loudnessGainMb": 400,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "BASS",
        "displayName": "Bass",
        "emoji": "◉",
        "description": "Heavy sub & bass boost for earphones",
        "bands": [800, 600, 0, -100, -100],
        "loudnessGainMb": 600,
        "smartTunnel": False,
        "spatialAudio": False
    },
    {
        "name": "SPATIAL",
        "displayName": "Spatial",
        "emoji": "🎧",
        "description": "Stereo widening for immersive headphone listening",
        "bands": [100, 0, 50, 150, 200],
        "loudnessGainMb": 300,
        "smartTunnel": False,
        "spatialAudio": True
    }
]
