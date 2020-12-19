
from __future__ import annotations

import logging
import random
from typing import Dict, MutableMapping, Optional, Protocol, Union

import aiohttp
import discord
from discord.ext import commands

from .exceptions import NodeCreationError, NodeNotFound, NodesNotFound
from .node import Node
from .player import Player

__log__ = logging.getLogger(__name__)


class Client:

    def __init__(self, *, bot: Union[commands.Bot, commands.AutoShardedBot], session: aiohttp.ClientSession = None) -> None:

        self._bot = bot
        self._session = session or aiohttp.ClientSession()

        self._nodes: Dict[str, Node] = {}

    def __repr__(self) -> str:
        return f'<slate.Client node_count={len(self.nodes)} player_count={len(self.players)}>'

    #

    @property
    def bot(self) -> Union[commands.Bot, commands.AutoShardedBot]:
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def nodes(self) -> MutableMapping[str, Node]:
        return self._nodes

    #

    @property
    def players(self) -> MutableMapping[int, Player]:

        players = []
        for node in self.nodes.values():
            players.extend(node.players.values())

        return {player.guild.id: player for player in players}

    #

    async def create_node(self, *, host: str, port: str, password: str, identifier: str, andesite: bool = False, lavalink_compatibility: bool = False) -> Node:

        await self.bot.wait_until_ready()

        if identifier in self.nodes.keys():
            raise NodeCreationError(f'Node with identifier \'{identifier}\' already exists.')

        node = Node(client=self, host=host, port=port, password=password, identifier=identifier, andesite=andesite, lavalink_compatibility=lavalink_compatibility)
        await node.connect()

        return node

    def get_node(self, *, identifier: str = None) -> Optional[Node]:

        available_nodes = {identifier: node for identifier, node in self._nodes.items() if node.is_connected}
        if not available_nodes:
            raise NodesNotFound('There are no Nodes available.')

        if identifier is None:
            return random.choice([node for node in available_nodes.values()])

        return available_nodes.get(identifier, None)

    async def create_player(self, *, channel: discord.VoiceChannel) -> Protocol[Player]:

        node = self.get_node()
        if not node:
            raise NodeNotFound('There are no nodes available.')

        player = await channel.connect(cls=Player)
        player.node = node

        node.players[channel.guild.id] = player
        return player

    def get_player(self, *, guild: discord.Guild) -> Optional[Protocol[Player]]:
        return self.players.get(guild.id, None)
