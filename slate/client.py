
from __future__ import annotations

import logging
import random
from typing import Dict, MutableMapping, Optional, Protocol, Type

import aiohttp
import discord

from .andesite_node import AndesiteNode
from .bases import BaseNode
from .exceptions import NoNodesFound, NodeCreationError, NodeNotFound, PlayerAlreadyExists
from .player import Player

__log__ = logging.getLogger(__name__)


class Client:

    def __init__(self, *, bot: Protocol[discord.Client], session: aiohttp.ClientSession = None) -> None:

        self._bot: Protocol[discord.Client] = bot
        self._session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self._nodes: Dict[str, Protocol[BaseNode]] = {}

    def __repr__(self) -> str:
        return f'<slate.Client node_count={len(self.nodes)} player_count={len(self.players)}>'

    #

    @property
    def bot(self) -> Protocol[discord.Client]:
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    #

    @property
    def nodes(self) -> MutableMapping[str, Protocol[BaseNode]]:
        return self._nodes

    @property
    def players(self) -> MutableMapping[int, Protocol[Player]]:

        players = []
        for node in self.nodes.values():
            players.extend(node.players.values())

        return {player.guild.id: player for player in players}

    #

    async def create_node(self, *, host: str, port: str, password: str, identifier: str, use_compatibility: bool = False, cls: Protocol[Type[BaseNode]]) -> Protocol[BaseNode]:

        await self.bot.wait_until_ready()

        if identifier in self.nodes.keys():
            raise NodeCreationError(f'Node with identifier \'{identifier}\' already exists.')

        if not issubclass(cls, BaseNode):
            raise NodeCreationError('The \'node\' argument must be a subclass of \'slate.BaseNode\'.')

        if issubclass(cls, AndesiteNode):
            node = cls(client=self, host=host, port=port, password=password, identifier=identifier, use_compatibility=use_compatibility)
        else:
            node = cls(client=self, host=host, port=port, password=password, identifier=identifier)

        await node.connect()
        return node

    def get_node(self, *, identifier: str = None) -> Optional[Protocol[BaseNode]]:

        available_nodes = {identifier: node for identifier, node in self._nodes.items() if node.is_connected}
        if not available_nodes:
            raise NoNodesFound('There are no Nodes available.')

        if identifier is None:
            return random.choice([node for node in available_nodes.values()])

        return available_nodes.get(identifier, None)

    async def create_player(self, *, channel: discord.VoiceChannel, node_identifier: str = None) -> Protocol[Player]:

        node = self.get_node(identifier=node_identifier)
        if not node and node_identifier:
            raise NodeNotFound(f'Node with identifier \'{node_identifier}\' was not found.')

        if channel.guild in self.players.keys():
            raise PlayerAlreadyExists(f'Player for guild \'{channel.guild}\' already exists.')

        player = await channel.connect(cls=Player)
        player._node = node

        node._players[channel.guild.id] = player
        return player

    def get_player(self, *, guild: discord.Guild) -> Optional[Protocol[Player]]:
        return self.players.get(guild.id, None)
