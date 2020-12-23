
from __future__ import annotations

import logging
import random
import typing
from typing import Dict, Mapping, Optional, Protocol, Type

import aiohttp
import discord

from .andesite_node import AndesiteNode
from .bases import BaseNode
from .exceptions import NoNodesFound, NodeCreationError, NodeNotFound, PlayerAlreadyExists
from .player import Player

__log__ = logging.getLogger(__name__)


class Client:
    """The client used to manage Lavalink or Andesite nodes and their players.

    Parameters
    ----------
    bot: :py:class:`Protocol` [ :py:class:`discord.Client` ]
        The bot instance that this :class:`Client` should be connected to.
    session: :py:class:`Optional` [ :py:class:`aiohttp.ClientSession` ]
        The aiohttp session used to make requests and connect to websockets. If not passed a new one will be made.
    """

    def __init__(self, *, bot: Protocol[discord.Client], session: Optional[aiohttp.ClientSession] = None) -> None:

        self._bot: Protocol[discord.Client] = bot
        self._session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self._nodes: Dict[str, Protocol[BaseNode]] = {}

    def __repr__(self) -> str:
        return f'<slate.Client node_count={len(self.nodes)} player_count={len(self.players)}>'

    #

    @property
    def bot(self) -> Protocol[discord.Client]:
        """:py:class:`Protocol` [ :py:class:`discord.Client` ]: The bot instance that this :class:`Client` is connected to."""
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        """:py:class:`aiohttp.ClientSession`: The aiohttp session used to make requests and connect to :class:`BaseNode` websockets."""
        return self._session

    #

    @property
    def nodes(self) -> Mapping[str, Protocol[BaseNode]]:
        """A mapping of :py:attr:`BaseNode.identifier` to :py:class:`typing.Protocol` [ :py:class:`BaseNode` ]'s."""
        return self._nodes

    @property
    def players(self) -> Mapping[int, Protocol[Player]]:
        """A mapping of :py:attr:`Player.guild.id` to :py:class:`typing.Protocol` [ :py:class:`Player` ]'s."""

        players = []
        for node in self.nodes.values():
            players.extend(node.players.values())

        return {player.guild.id: player for player in players}

    #

    async def create_node(self, *, host: str, port: str, password: str, identifier: str, cls: Protocol[Type[BaseNode]], **kwargs) -> Protocol[BaseNode]:
        """Creates and attempts to connect to a :py:class:`Protocol` [ :py:class:`BaseNode` ].

        Parameters
        ----------
        host: :py:class:`str`
            The host address to attempt connection with.
        port: :py:class:`int`
            The port to attempt connection with.
        password: :py:class:`str`
            The password used for authentification.
        identifier: :py:class:`str`
            A unique identifier used to refer to the :py:class:`Protocol` [ :py:class:`BaseNode` ].
        cls: :py:class:`Protocol` [ :py:class:`Type` [ :py:class:`BaseNode` ] ]
            The class used to connect to the node with. Must be a subclass of :py:class:`BaseNode`.
        **kwargs:
            Optional keyword arguments to pass to the :py:class:`Protocol` [ :py:class:`BaseNode` ].
        """

        await self.bot.wait_until_ready()

        if identifier in self.nodes.keys():
            raise NodeCreationError(f'Node with identifier \'{identifier}\' already exists.')

        if not issubclass(cls, BaseNode):
            raise NodeCreationError(f'The \'node\' argument must be a subclass of \'{BaseNode.__name__}\'.')

        node = cls(client=self, host=host, port=port, password=password, identifier=identifier, **kwargs)
        __log__.debug(f'Node | Attempting \'{node.__name__}\' connection with identifier \'{identifier}\'.')

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
            raise PlayerAlreadyExists(f'Player for guild \'{channel.guild!r}\' already exists.')

        __log__.debug(f'Player | Attempting player creation for guild: {channel.guild!r}')

        player = await channel.connect(cls=Player)
        player._node = node

        node._players[channel.guild.id] = player
        return player

    def get_player(self, *, guild: discord.Guild) -> Optional[Protocol[Player]]:
        return self.players.get(guild.id, None)
