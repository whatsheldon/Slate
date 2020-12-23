
from __future__ import annotations

import logging
import random
from typing import MutableMapping, Optional, Protocol, Type

import aiohttp
import discord

from .bases import BaseNode
from .exceptions import NoNodesAvailable, NodeCreationError, NodeNotFound, PlayerAlreadyExists
from .player import Player

__log__ = logging.getLogger(__name__)


class Client:
    """The client used to manage Lavalink or Andesite nodes and their players.

    Parameters
    ----------
    bot: :py:class:`Protocol` [ :py:class:`discord.Client` ]
        The bot instance that this :class:`Client` should be connected to.
    session: :py:class:`Optional` [ :py:class:`aiohttp.ClientSession` ]
        The aiohttp session used to make requests and connect to websockets with. If not passed, a new one will be made.
    """

    def __init__(self, *, bot: Protocol[discord.Client], session: Optional[aiohttp.ClientSession] = None) -> None:

        self._bot: Protocol[discord.Client] = bot
        self._session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self._nodes: MutableMapping[str, Protocol[BaseNode]] = {}

    def __repr__(self) -> str:
        return f'<slate.Client node_count={len(self.nodes)} player_count={len(self.players)}>'

    #

    @property
    def bot(self) -> Protocol[discord.Client]:
        """:py:class:`Protocol` [ :py:class:`discord.Client` ]: The bot instance that this :class:`Client` is connected to."""
        return self._bot

    @property
    def session(self) -> aiohttp.ClientSession:
        """:py:class:`aiohttp.ClientSession`: The aiohttp session used to make requests and connect to Node websockets with."""
        return self._session

    #

    @property
    def nodes(self) -> MutableMapping[str, Protocol[BaseNode]]:
        """A mapping of :py:attr:`BaseNode.identifier`'s to :py:class:`typing.Protocol` [ :py:class:`BaseNode` ]'s."""
        return self._nodes

    @property
    def players(self) -> MutableMapping[int, Protocol[Player]]:
        """A mapping of :py:attr:`Player.guild.id`'s to :py:class:`typing.Protocol` [ :py:class:`Player` ]'s."""

        players = []
        for node in self.nodes.values():
            players.extend(node.players.values())

        return {player.guild.id: player for player in players}

    #

    async def create_node(self, *, host: str, port: str, password: str, identifier: str, cls: Protocol[Type[BaseNode]], **kwargs) -> Protocol[BaseNode]:
        """Creates a :py:class:`Protocol` [ :py:class:`BaseNode` ] and attempts to connect to an external nodes websocket.

        Parameters
        ----------
        host: :py:class:`str`
            The host address to attempt connection with.
        port: :py:class:`int`
            The port to attempt connection with.
        password: :py:class:`str`
            The password used for authentification.
        identifier: :py:class:`str`
            A unique identifier used to refer to the created Node.
        cls: :py:class:`Protocol` [ :py:class:`Type` [ :py:class:`BaseNode` ] ]
            The class used to supply logic to connect to the external node with. Must be a subclass of :py:class:`BaseNode`.
        **kwargs:
            Optional keyword arguments to pass to the created Node.

        Returns
        -------
        :py:class:`Protocol` [ :py:class:`BaseNode` ]
            The Node that was created.

        Raises
        ------
        :py:class:`NodeCreationError`
            Either a Node with the given identifier already exists, or the given class was not a subclass of :py:class:`BaseNode`.
        :py:class:`NodeConnectionError`
            There was an error while connecting to the external node. Could be invalid authorization or an incorrect host address/port, etc.
        """

        await self.bot.wait_until_ready()

        if identifier in self.nodes.keys():
            raise NodeCreationError(f'Node with identifier \'{identifier}\' already exists.')

        if not issubclass(cls, BaseNode):
            raise NodeCreationError(f'The \'node\' argument must be a subclass of \'{BaseNode.__name__}\'.')

        node = cls(client=self, host=host, port=port, password=password, identifier=identifier, **kwargs)
        __log__.debug(f'Node | Attempting \'{node.__class__.__name__}\' connection with identifier \'{identifier}\'.')

        await node.connect()
        return node

    def get_node(self, *, identifier: str = None) -> Optional[Protocol[BaseNode]]:
        """Attempts to return a :py:class:`Protocol` [ :py:class:`BaseNode` ] with the given identifier.

        Parameters
        ----------
        identifier: :py:class:`Optional` [ :py:class:`str` ]
            The identifier of the Node to return. If None a random Node will be returned.

        Returns
        -------
        :py:class:`Optional` [ :py:class:`Protocol` [ :py:class:`BaseNode` ] ]
            The Node with the given identifier. Could return None if no Nodes are found.

        Raises
        ------
        :py:class:`NoNodesAvailable`
            Raised if there are no Nodes available.
        """

        available_nodes = {identifier: node for identifier, node in self._nodes.items() if node.is_connected}
        if not available_nodes:
            raise NoNodesAvailable('There are no Nodes available.')

        if identifier is None:
            return random.choice([node for node in available_nodes.values()])

        return available_nodes.get(identifier, None)

    async def create_player(self, *, channel: discord.VoiceChannel, node_identifier: str = None, cls: Optional[Protocol[Type[Player]]] = Player) -> Protocol[Player]:
        """Creates a :py:class:`Protocol` [ :py:class:`Player` ] for the given :py:class:`discord.VoiceChannel`.

        Parameters
        ----------
        channel: :py:class:`discord.VoiceChannel`
            The discord voice channel to create the player for.
        node_identifier: :py:class:`Optional` [ :py:class:`str` ]
            An optional Node identifier to create the player with. If not passed a random Node will be chosen.
        cls: :py:class:`Protocol` [ :py:class:`Type` [ :py:class:`Player` ] ]
            The class used to base the player upon. Must be a subclass of :py:class:`Player`.

        Returns
        -------
        :py:class:`Protocol` [ :py:class:`Player` ]
            The Player that was created.

        Raises
        ------
        :py:class:`NoNodesAvailable`
            Raised if there are no Nodes available.
        :py:class:`NodeNotFound`
            Raised if a Node with the given identifier was not found.
        :py:class:`PlayerAlreadyExists`
            Raised if a player for the guild the :py:class:`discord.VoiceChannel` is in already exists.
        """

        node = self.get_node(identifier=node_identifier)
        if not node and node_identifier:
            raise NodeNotFound(f'Node with identifier \'{node_identifier}\' was not found.')

        if channel.guild.id in self.players.keys():
            raise PlayerAlreadyExists(f'Player for guild \'{channel.guild!r}\' already exists.')

        __log__.debug(f'Player | Attempting player creation for guild: {channel.guild!r}')

        player = await channel.connect(cls=cls)
        player._node = node

        node._players[channel.guild.id] = player
        return player

    def get_player(self, *, guild: discord.Guild) -> Optional[Protocol[Player]]:
        """Attempts to return the :py:class:`Protocol` [ :py:class:`Player` ] for the given :py:class:`discord.Guild`

        Parameters
        ----------
        guild: :py:class:`discord.Guild`
            The discord guild to return the Player for.

        Returns
        -------
        :py:class:`Optional` [ :py:class:`Protocol` [ :py:class:`Player` ] ]
            The Player for the given discord guild. Could be None if the guild does not already have a Player.
        """
        return self.players.get(guild.id, None)
