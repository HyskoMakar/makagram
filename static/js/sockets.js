(function () {
    'use strict';

    function getScheme() {
        return window.location.protocol === 'https:'
            ? 'wss'
            : 'ws';
    }

    function createSocket(path) {
        return new WebSocket(
            getScheme() +
            '://' +
            window.location.host +
            path
        );
    }

    function createPrivateChatSocket(username) {
        return createSocket(
            '/ws/privatechat/' +
            encodeURIComponent(username) +
            '/'
        );
    }

    function createGroupSocket(groupId) {
        return createSocket(
            '/ws/group/' +
            groupId +
            '/'
        );
    }

    function createChannelSocket(channelId) {
        return createSocket(
            '/ws/channel/' +
            channelId +
            '/'
        );
    }

    function createLobbySocket(roomName) {
        return createSocket(
            '/ws/lobby/' +
            encodeURIComponent(roomName) +
            '/'
        );
    }

    function send(socket, data) {
        if (
            !socket ||
            socket.readyState !== WebSocket.OPEN
        ) {
            return false;
        }

        socket.send(
            JSON.stringify(data)
        );

        return true;
    }

    window.MakaSockets = {
        createSocket,
        createPrivateChatSocket,
        createGroupSocket,
        createChannelSocket,
        createLobbySocket,
        send
    };
})();