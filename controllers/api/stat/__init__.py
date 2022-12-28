# Copyright (C) tiksan - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by tiksan <webmaster@deek.sh>

import random

from flask import jsonify, request
from mongoengine.queryset import QuerySet
from mongoengine.queryset.visitor import Q

from controllers.api.decorators import key_required, ratelimit, requires_scopes
from controllers.api.utils import api_ratelimit_response, make_exception_response
from models.factionmodel import FactionModel
from models.statmodel import StatModel
from models.user import User


@key_required
@ratelimit
@requires_scopes(scopes={"admin", "read:stats"})
def generate_chain_list(*args, **kwargs):
    key = f'tornium:ratelimit:{kwargs["user"].tid}'

    defender_stats = request.args.get("dstats") if request.args.get("dstats") is not None else 0.75
    variance = request.args.get("variance") if request.args.get("variance") is not None else 0.01

    if kwargs["user"].battlescore == 0:
        return make_exception_response(
            "0000",
            key,
            details={"message": "User does not have a stat score stored in the database."},
        )

    stat_entries = StatModel.objects(
        (Q(globalstat=True) | Q(addedid=kwargs["user"].tid) | Q(addedfactiontid=kwargs["user"].factionid))
        & Q(battlescore__gte=(kwargs["user"]["battlescore"] * (defender_stats - variance)))
        & Q(battlescore__lte=(kwargs["user"]["battlescore"] * (defender_stats + variance)))
    )
    stat_entries = list(set(stat_entries.all().values_list("tid")))
    random.shuffle(stat_entries)
    jsonified_stat_entires = []

    targets = {}
    targets_updated = 0

    for stat_entry in stat_entries:
        stat: StatModel = (
            StatModel.objects(
                Q(tid=stat_entry)
                & (Q(globalstat=True) | Q(addedid=kwargs["user"].tid) | Q(addedfactiontid=kwargs["user"].factionid))
            )
            .order_by("-timeadded")
            .first()
        )

        if stat_entry in targets:
            user = targets[stat_entry]
        else:
            user = User(tid=stat.tid)

            if targets_updated <= 50:
                if user.refresh(key=kwargs["user"].key):
                    targets_updated += 1

        jsonified_stat_entires.append(
            {
                "statid": stat.statid,
                "tid": stat.tid,
                "battlescore": stat.battlescore,
                "timeadded": stat.timeadded,
                "user": {
                    "tid": user.tid,
                    "name": user.name,
                    "username": f"{user.name} [{user.tid}]",
                    "level": user.level,
                    "last_refresh": user.last_refresh,
                    "factionid": user.factiontid,
                    "status": user.status,
                    "last_action": user.last_action,
                },
            }
        )

    return (
        jsonify(
            {
                "defender_stats": defender_stats,
                "variance": variance,
                "data": jsonified_stat_entires,
            }
        ),
        200,
        api_ratelimit_response(key),
    )


@key_required
@ratelimit
@requires_scopes(scopes={"admin", "read:stats"})
def get_stat_user(tid, *args, **kwargs):
    key = f'tornium:ratelimit:{kwargs["user"].tid}'

    stat_entries: QuerySet = (
        StatModel.objects(
            Q(tid=tid)
            & (Q(globalstat=True) | Q(addedid=kwargs["user"].tid) | Q(addedfactiontid=kwargs["user"].factionid))
        )
        .order_by("-statid")
        .exclude("tid")
        .all()
    )

    data = {"user": {}, "stat_entries": {}}

    user = User(tid)
    user.refresh(key=kwargs["user"].key)

    data["user"] = {
        "tid": user.tid,
        "name": user.name,
        "level": user.level,
        "last_refresh": user.last_refresh,
        "discord_id": user.discord_id,
        "factiontid": user.factiontid,
        "status": user.status,
        "last_action": user.last_action,
    }

    factions = {}

    stat_entry: StatModel
    for stat_entry in stat_entries:
        if stat_entry.addedfactiontid == 0:
            faction = None
        elif str(stat_entry.addedfactiontid) in factions:
            faction = factions[str(stat_entry.addedfactiontid)]
        else:
            faction_db: FactionModel = FactionModel.objects(tid=stat_entry.addedfactiontid).first()

            if faction_db is None:
                faction = None
                factions[str(stat_entry.addedfactiontid)] = None
            else:
                faction = {
                    "name": faction_db.name,
                    "respect": faction_db.respect,
                    "capacity": faction_db.capacity,
                    "leader": faction_db.leader,
                    "coleader": faction_db.coleader,
                }
                factions[str(stat_entry.addedfactiontid)] = faction

        data["stat_entries"][stat_entry.statid] = {
            "stat_score": stat_entry.battlescore,
            "timeadded": stat_entry.timeadded,
            "addedid": stat_entry.addedid,
            "addedfaction": faction,
            "addedfactiontid": stat_entry.addedfactiontid,
            "globalstat": stat_entry.globalstat,
        }

    return (jsonify(data), 200, api_ratelimit_response(key))
