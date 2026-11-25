"""
Envoie un verset du Coran au hasard sur un webhook Discord.
Lancé automatiquement par GitHub Actions (voir verset.yml).

Données : API gratuite AlQuran Cloud (https://alquran.cloud/api)
"""

import json
import os
import random
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://api.alquran.cloud/v1"
# texte arabe, traduction française (Hamidullah), récitation audio (Mishary Alafasy)
EDITIONS = "quran-uthmani,fr.hamidullah,ar.alafasy"
UA = {"User-Agent": "rappel-coran/1.0"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def charger_config():
    with open("config.json", encoding="utf-8") as f:
        return json.load(f)


def dans_les_heures_actives(config):
    """Renvoie False si on est en dehors de la plage horaire choisie (heure de Paris)."""
    debut, fin = config.get("heures_actives", [0, 24])
    heure = datetime.now(ZoneInfo("Europe/Paris")).hour
    return debut <= heure < fin


def tirer_verset(config):
    sourates = config.get("sourates", [])
    if sourates:
        n = random.choice(sourates)
        data = get_json(f"{API}/surah/{n}/editions/{EDITIONS}")["data"]
        i = random.randrange(len(data[0]["ayahs"]))
        arabe, fr, audio = (d["ayahs"][i] for d in data)
        sourate = data[0]
    else:
        n = random.randint(1, 6236)  # 6236 versets au total
        arabe, fr, audio = get_json(f"{API}/ayah/{n}/editions/{EDITIONS}")["data"]
        sourate = arabe["surah"]

    texte_arabe = f"||{arabe['text']}||" if config.get("masque") else arabe["text"]
    embed = {
        "title": f"{sourate['englishName']} ({sourate['name']}) — {sourate['number']}:{arabe['numberInSurah']}",
        "description": f"{texte_arabe}\n\n{fr['text']}",
        "color": 0x2E8B57,
    }
    if audio.get("audio"):
        embed["fields"] = [{"name": "Écouter", "value": f"[Récitation audio]({audio['audio']})"}]
    return embed


def envoyer(webhook_url, embed):
    payload = json.dumps({"username": "Rappel Coran", "embeds": [embed]}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", **UA},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


if __name__ == "__main__":
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        sys.exit("Variable DISCORD_WEBHOOK_URL manquante.")

    config = charger_config()
    manuel = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if not manuel and not dans_les_heures_actives(config):
        print("En dehors des heures actives, rien à envoyer.")
        sys.exit(0)

    envoyer(webhook, tirer_verset(config))
    print("Verset envoyé.")
