# Copyright (C) 2021-2023 tiksan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import operator
import random
import time
import typing

import requests

from tornium_celery.tasks.api import discordpatch, discordpost, tornget
from tornium_commons.errors import NetworkingError, TornError
from tornium_commons.formatters import find_list
from tornium_commons.models import FactionModel, UserModel
from tornium_commons.skyutils import SKYNET_ERROR, SKYNET_INFO

from skynet.skyutils import get_admin_keys


def faction_data_switchboard(interaction, *args, **kwargs):
    if interaction["data"]["options"][0]["name"] == "members":
        return members_switchboard(interaction, *args, **kwargs)

    return {}


def members_switchboard(interaction, *args, **kwargs):
    payload = [
        {
            "title": "",
            "description": "",
            "color": SKYNET_INFO,
        }
    ]

    def online():
        payload[0]["title"] = f"Online Members of {member_data['name']}"
        indices = sorted(
            member_data["members"], key=lambda d: member_data["members"][d]["last_action"]["timestamp"], reverse=True
        )
        member_data["members"] = {n: member_data["members"][n] for n in indices}

        for tid, member in member_data["members"].items():
            tid = int(tid)

            if member["last_action"]["status"] == "Online":
                line_payload = f"{member['name']} [{tid}] - Online - {member['last_action']['relative']}"
            elif (
                member["last_action"]["status"] == "Idle"
                and int(time.time()) - member["last_action"]["timestamp"] < 600
            ):  # Ten minutes
                line_payload = f"{member['name']} [{tid}] - Idle - {member['last_action']['relative']}"
            else:
                continue

            if (len(payload[-1]["description"]) + 1 + len(line_payload)) > 4096:
                payload.append(
                    {
                        "title": f"Online Members of {member_data['name']}",
                        "description": "",
                        "color": SKYNET_INFO,
                    }
                )
            else:
                line_payload = "\n" + line_payload

            payload[-1]["description"] += line_payload

        discordpatch(
            endpoint=f"webhooks/{interaction['application_id']}/{interaction['token']}/messages/@original",
            payload={"embeds": payload},
        )

    def offline():
        payload[0]["title"] = f"Offline Members of {member_data['name']}"
        indices = sorted(
            member_data["members"], key=lambda d: member_data["members"][d]["last_action"]["timestamp"], reverse=True
        )
        member_data["members"] = {n: member_data["members"][n] for n in indices}

        for tid, member in member_data["members"].items():
            tid = int(tid)

            if member["last_action"]["status"] == "Offline":
                line_payload = f"{member['name']} [{tid}] - Offline - {member['last_action']['relative']}"
            elif (
                member["last_action"]["status"] == "Idle"
                and int(time.time()) - member["last_action"]["timestamp"] <= 600
            ):  # Ten minutes
                line_payload = f"{member['name']} [{tid}] - Idle - {member['last_action']['relative']}"
            else:
                continue

            if (len(payload[-1]["description"]) + 1 + len(line_payload)) > 4096:
                payload.append(
                    {
                        "title": f"Offline Members of {member_data['name']}",
                        "description": "",
                        "color": SKYNET_INFO,
                    }
                )
            else:
                line_payload = "\n" + line_payload

            payload[-1]["description"] += line_payload

        discordpatch(
            endpoint=f"webhooks/{interaction['application_id']}/{interaction['token']}/messages/@original",
            payload={"embeds": payload},
        )

    def flying():
        payload[0]["title"] = f"Abroad Members of {member_data['name']}"
        indices = sorted(
            member_data["members"], key=lambda d: member_data["members"][d]["last_action"]["timestamp"], reverse=True
        )
        member_data["members"] = {n: member_data["members"][n] for n in indices}

        for tid, member in member_data["members"].items():
            tid = int(tid)

            if member["status"]["state"] in ("Traveling", "Abroad"):
                line_payload = f"{member['name']} [{tid}] - {member['status']['description']} - {member['last_action']['relative']}"
            else:
                continue

            if (len(payload[-1]["description"]) + 1 + len(line_payload)) > 4096:
                payload.append(
                    {
                        "title": f"Abroad Members of {member_data['name']}",
                        "description": "",
                        "color": SKYNET_INFO,
                    }
                )
            else:
                line_payload = "\n" + line_payload

            payload[-1]["description"] += line_payload

        discordpatch(
            endpoint=f"webhooks/{interaction['application_id']}/{interaction['token']}/messages/@original",
            payload={"embeds": payload},
        )

    def okay():
        payload[0]["title"] = f"Okay Members of {member_data['name']}"
        indices = sorted(
            member_data["members"], key=lambda d: member_data["members"][d]["last_action"]["timestamp"], reverse=True
        )
        member_data["members"] = {n: member_data["members"][n] for n in indices}

        for tid, member in member_data["members"].items():
            tid = int(tid)

            if member["last_action"]["status"] == "Okay":
                line_payload = f"{member['name']} [{tid}] - {member['last_action']['status']} - {member['last_action']['relative']}"
            else:
                continue

            if (len(payload[-1]["description"]) + 1 + len(line_payload)) > 4096:
                payload.append(
                    {
                        "title": f"Okay Members of {member_data['name']}",
                        "description": "",
                        "color": SKYNET_INFO,
                    }
                )
            else:
                line_payload = "\n" + line_payload

            payload[-1]["description"] += line_payload

        discordpatch(
            endpoint=f"webhooks/{interaction['application_id']}/{interaction['token']}/messages/@original",
            payload={"embeds": payload},
        )

    def hospital():
        return {}

    def inactive():
        days: typing.Union[dict, int] = find_list(subcommand_data, "name", "days")

        if days == -1:
            days = 3
        else:
            days = days[1]["value"]

        payload[0]["title"] = f"Inactive Members of {member_data['name']}"
        indices = sorted(
            member_data["members"], key=lambda d: member_data["members"][d]["last_action"]["timestamp"], reverse=True
        )
        member_data["members"] = {n: member_data["members"][n] for n in indices}

        for tid, member in member_data["members"].items():
            tid = int(tid)

            if int(time.time()) - member["last_action"]["timestamp"] >= days * 24 * 60 * 60:
                line_payload = f"{member['name']} [{tid}] - {member['last_action']['relative']}"
            else:
                continue

            if (len(payload[-1]["description"]) + 1 + len(line_payload)) > 4096:
                payload.append(
                    {
                        "title": f"Inactive Members of {member_data['name']}",
                        "description": "",
                        "color": SKYNET_INFO,
                    }
                )
            else:
                line_payload = "\n" + line_payload

            payload[-1]["description"] += line_payload

        discordpatch(
            endpoint=f"webhooks/{interaction['application_id']}/{interaction['token']}/messages/@original",
            payload={"embeds": payload},
        )

    try:
        subcommand = interaction["data"]["options"][0]["options"][0]["name"]
        subcommand_data = interaction["data"]["options"][0]["options"][0]["options"]
    except Exception:
        return {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "Invalid Interaction Format",
                        "description": "Discord has returned an invalidly formatted interaction.",
                        "color": SKYNET_ERROR,
                    }
                ],
                "flags": 64,  # Ephemeral
            },
        }

    user: UserModel = kwargs["invoker"]
    faction: typing.Union[dict, int] = find_list(subcommand_data, "name", "faction")

    if faction == -1:
        faction: typing.Optional[FactionModel] = FactionModel.objects(tid=user.factionid).first()

        if faction is None:
            return {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Faction Not Found",
                            "description": "The faction could not be located in the database. This error is not "
                            "currently handled.",
                            "color": SKYNET_ERROR,
                        }
                    ],
                    "flags": 64,  # Ephemeral
                },
            }
    elif faction[1]["value"].isdigit():
        faction: typing.Optional[FactionModel] = FactionModel.objects(tid=int(faction[1]["value"])).first()

        if faction is None:
            return {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Faction Not Found",
                            "description": "This faction could not be located in the database by name.",
                            "color": SKYNET_ERROR,
                        }
                    ],
                    "flags": 64,  # Ephemeral
                },
            }
    else:
        faction: typing.Optional[FactionModel] = FactionModel.objects(name__iexact=faction[1]["value"]).first()

        if faction is None:
            return {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Faction Not Found",
                            "description": "This faction could not be located in the database by name.",
                            "color": SKYNET_ERROR,
                        }
                    ],
                    "flags": 64,  # Ephemeral
                },
            }

    admin_keys = get_admin_keys(interaction)

    if len(admin_keys) == 0:
        return {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "No API Keys",
                        "description": "No API keys of admins could be located. Please sign into Tornium or ask a server admin to sign in.",
                        "color": SKYNET_ERROR,
                    }
                ],
                "flags": 64,
            },
        }

    try:
        discordpost(
            f"interactions/{interaction['id']}/{interaction['token']}/callback",
            payload={"type": 5},
        )
    except requests.exceptions.JSONDecodeError:
        pass
    except json.JSONDecodeError:
        pass

    try:
        member_data = tornget(
            f"faction/{faction.tid}?selections=",
            key=random.choice(admin_keys),
        )
    except TornError as e:
        return {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "Torn API Error",
                        "description": f'The Torn API has raised error code {e.code}: "{e.message}".',
                        "color": SKYNET_ERROR,
                    }
                ],
                "flags": 64,  # Ephemeral
            },
        }
    except NetworkingError as e:
        return {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "HTTP Error",
                        "description": f'The Torn API has returned an HTTP error {e.code}: "{e.message}".',
                        "color": SKYNET_ERROR,
                    }
                ],
                "flags": 64,  # Ephemeral
            },
        }

    if subcommand == "online":
        return online()
    elif subcommand == "offline":
        return offline()
    elif subcommand == "flying":
        return flying()
    elif subcommand == "okay":
        return okay()
    elif subcommand == "hospital":
        return hospital()
    elif subcommand == "inactive":
        return inactive()
    else:
        return {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "Command Not Found",
                        "description": "This command does not exist.",
                        "color": SKYNET_ERROR,
                    }
                ],
                "flags": 64,  # Ephemeral
            },
        }
