"""Approved public destinations and separately assigned affiliate channels."""
from datetime import datetime, timezone


AQUAFUNDED_CHANNELS = {
    'OES-ChaseInGreen-Website': 'https://www.aquafunded.com/?afmc=121w',
    'OES-LinkedIn': 'https://www.aquafunded.com/?afmc=121x',
    'FlareUpProfits-Discord': 'https://www.aquafunded.com/?afmc=1220',
    'OES-Facebook': 'https://www.aquafunded.com/?afmc=1221',
    'OES-Instagram': 'https://www.aquafunded.com/?afmc=1222',
    'OES-YouTube': 'https://www.aquafunded.com/?afmc=1223',
    'OES-DirectReferral': 'https://www.aquafunded.com/?afmc=1224',
    'OES-ChaseInGreen-App': 'https://www.aquafunded.com/?afmc=1225',
}
AQUAFUNDED_WEBSITE = AQUAFUNDED_CHANNELS['OES-ChaseInGreen-Website']

# Provider timestamps are recorded in UTC. Verify replacement codes before editing.
COMMUNITY_INVITES = {
    'chaseingreen': ('https://discord.gg/NAW9CtSG4', '2026-12-25T21:02:50+00:00'),
    'lottovate': ('https://discord.gg/CmvTKBPNc', '2026-12-25T21:02:58+00:00'),
}


def active_community_invites(now=None):
    now = now or datetime.now(timezone.utc)
    return {product: url for product, (url, expires) in COMMUNITY_INVITES.items()
            if now < datetime.fromisoformat(expires)}
