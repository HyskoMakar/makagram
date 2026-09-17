(function () {
    'use strict';

    const URL_PATTERN =
        /((?:https?:\/\/|www\.|\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|dev|app|co|ai|ru|uk|de|fr|me|tv|gg|ly|sh|to|cloud|online|site|store|tech|info|biz|xyz))(?:\/[^\s<]*)?)([.,\)!?;:]?(?:\s|<|$))/gi;

    const MENTION_PATTERN =
        /@([A-Za-z0-9_-]{1,50})/g;


    function escapeHtml(str) {

        const div =
            document.createElement('div');

        div.textContent =
            str || '';

        return div.innerHTML;
    }


    function autolink(text, options) {

        options = options || {};

        const knownUsers =
            options.knownUsers ||
            null;

        if (!text) {
            return '';
        }

        let result =
            escapeHtml(text);

        result =
            result.replace(
                URL_PATTERN,
                (match, url, trailing) => {

                    const href =
                        /^https?:\/\//i.test(url)
                            ? url
                            : `https://${url}`;

                    return `
                        <a
                            href="${href}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-emerald-600 underline hover:text-emerald-800 break-all"
                            onclick="event.stopPropagation();"
                        >
                            ${url}
                        </a>${trailing}
                    `;
                }
            );

        if (knownUsers) {

            result =
                result.replace(
                    MENTION_PATTERN,
                    (match, username) => {

                        if (
                            knownUsers.has(
                                username
                            )
                        ) {

                            return `
                                <a
                                    href="/chat/private/${encodeURIComponent(username)}/"
                                    class="text-emerald-600 font-medium hover:underline"
                                    onclick="event.stopPropagation();"
                                >
                                    @${escapeHtml(username)}
                                </a>
                            `;
                        }

                        return match;
                    }
                );
        }

        return result;
    }


    function renderAttachmentsHTML(
        attachments,
        options
    ) {

        options = options || {};

        if (
            !attachments ||
            !attachments.length
        ) {
            return '';
        }

        return attachments
            .map(att => {

                if (att.is_image) {

                    return `
                        <a
                            href="${escapeHtml(att.url)}"
                            target="_blank"
                            class="block"
                        >
                            <img
                                src="${escapeHtml(att.url)}"
                                class="rounded-lg max-h-60 max-w-full object-cover border shadow-sm"
                            >
                        </a>
                    `;
                }

                return `
                    <a
                        href="${escapeHtml(att.url)}"
                        download="${escapeHtml(att.name || '')}"
                        target="_blank"
                        class="flex items-center gap-2.5 p-2 bg-white/80 hover:bg-white border rounded-lg text-gray-800 transition-colors group shadow-sm"
                    >

                        <svg
                            class="w-6 h-6 text-gray-500 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M7 21h10a2 2 0 002-2V7.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 1H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                            />
                        </svg>

                        <div class="flex flex-col min-w-0 flex-1">

                            <span class="text-xs font-medium truncate group-hover:underline">
                                ${escapeHtml(att.name || '')}
                            </span>

                            <span class="text-[10px] text-gray-500">
                                ${escapeHtml(att.size || '')}
                            </span>

                        </div>

                        <svg
                            class="w-4 h-4 text-emerald-500 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                            />
                        </svg>

                    </a>
                `;
            })
            .join('');
    }


    function createAvatar(options) {

        options = options || {};

        const avatar =
            document.createElement('div');

        const username =
            options.username ||
            '?';

        const color =
            options.color ||
            'gray';

        const size =
            options.size ||
            '9';

        avatar.className =
            `w-${size} h-${size} rounded-full overflow-hidden flex items-center justify-center text-sm font-semibold text-white flex-shrink-0 bg-${color}-300`;

        if (options.avatarUrl) {

            const img =
                document.createElement('img');

            img.src =
                options.avatarUrl;

            img.className =
                'w-full h-full object-cover';

            img.alt =
                username;

            avatar.appendChild(img);

        } else {

            avatar.textContent =
                username
                    .slice(0, 1)
                    .toUpperCase();
        }

        return avatar;
    }


    function renderMessage(
        data,
        options
    ) {

        options = options || {};

        const currentUser =
            options.currentUser ||
            '';

        const knownUsers =
            options.knownUsers ||
            null;

        const myColor =
            options.myColor ||
            'gray';

        const user =
            data.user ||
            {};

        const username =
            user.username ||
            data.username ||
            '?';

        const isMe =
            username === currentUser;

        const wrapper =
            document.createElement('div');

        wrapper.className =
            'flex items-start gap-2' +
            (
                isMe
                    ? ' justify-end'
                    : ''
            );

        if (data.message_id) {

            wrapper.dataset.messageId =
                data.message_id;
        }

        wrapper.dataset.username =
            username;

        wrapper.dataset.attachments =
            JSON.stringify(
                data.attachments || []
            );


        if (!isMe) {

            const avatar =
                createAvatar({
                    avatarUrl:
                        user.avatar ||
                        user.avatar_url ||
                        data.avatar,

                    username:
                        username,

                    color:
                        user.color ||
                        'gray',

                    size:
                        '9'
                });

            wrapper.appendChild(
                avatar
            );
        }


        const bubble =
            document.createElement('div');

        bubble.className =
            'chat-message-bubble px-3 py-2 rounded-lg text-sm max-w-xs break-words';


        if (isMe) {

            bubble.classList.add(
                `bg-${myColor}-100`,
                'text-gray-800'
            );

        } else {

            bubble.classList.add(
                'bg-gray-100',
                'text-gray-800'
            );

            const nameEl =
                document.createElement('div');

            nameEl.className =
                `text-xs font-medium text-${user.color || 'gray'}-500 mb-1`;

            nameEl.textContent =
                username;

            bubble.appendChild(
                nameEl
            );
        }


        const contentDiv =
            document.createElement('div');

        contentDiv.className =
            'msg-content whitespace-pre-wrap break-words' +
            (
                data.message
                    ? ''
                    : ' hidden'
            );

        contentDiv.innerHTML =
            autolink(
                data.message || '',
                {
                    knownUsers
                }
            );

        bubble.appendChild(
            contentDiv
        );


        const attDiv =
            document.createElement('div');

        attDiv.className =
            'msg-attachments flex flex-col gap-1.5' +
            (
                data.message &&
                data.attachments &&
                data.attachments.length
                    ? ' mt-2'
                    : ''
            );

        attDiv.innerHTML =
            renderAttachmentsHTML(
                data.attachments
            );

        bubble.appendChild(
            attDiv
        );


        if (isMe) {

            wrapper.appendChild(
                bubble
            );

            const avatar =
                createAvatar({
                    avatarUrl:
                        data.avatar,

                    username:
                        username,

                    color:
                        myColor,

                    size:
                        '9'
                });

            wrapper.appendChild(
                avatar
            );

        } else {

            wrapper.appendChild(
                bubble
            );
        }

        return wrapper;
    }


    function appendMessage(
        container,
        data,
        options
    ) {

        const element =
            renderMessage(
                data,
                options
            );

        container.appendChild(
            element
        );

        container.scrollTop =
            container.scrollHeight;

        return element;
    }


    function updateMessage(
        messageId,
        data,
        options
    ) {

        options = options || {};

        const wrapper =
            document.querySelector(
                `[data-message-id="${CSS.escape(String(messageId))}"]`
            );

        if (!wrapper) {
            return false;
        }

        wrapper.dataset.attachments =
            JSON.stringify(
                data.attachments || []
            );


        const contentEl =
            wrapper.querySelector(
                '.msg-content'
            );

        if (contentEl) {

            if (data.message) {

                contentEl.innerHTML =
                    autolink(
                        data.message,
                        {
                            knownUsers:
                                options.knownUsers
                        }
                    );

                contentEl.classList.remove(
                    'hidden'
                );

            } else {

                contentEl.innerHTML =
                    '';

                contentEl.classList.add(
                    'hidden'
                );
            }
        }


        const attEl =
            wrapper.querySelector(
                '.msg-attachments'
            );

        if (attEl) {

            attEl.innerHTML =
                renderAttachmentsHTML(
                    data.attachments
                );

            if (
                data.message &&
                data.attachments &&
                data.attachments.length
            ) {

                attEl.classList.add(
                    'mt-2'
                );

            } else {

                attEl.classList.remove(
                    'mt-2'
                );
            }
        }

        return true;
    }


    function deleteMessage(
        messageId
    ) {

        const wrapper =
            document.querySelector(
                `[data-message-id="${CSS.escape(String(messageId))}"]`
            );

        if (!wrapper) {
            return false;
        }

        wrapper.remove();

        return true;
    }


    function addSystemMessage(
        container,
        text
    ) {

        if (!container) {
            return;
        }

        const element =
            document.createElement('div');

        element.className =
            'text-center text-gray-500 text-sm py-2';

        element.textContent =
            text || '';

        container.appendChild(
            element
        );

        container.scrollTop =
            container.scrollHeight;
    }


    function appendLobbyMessage(
        container,
        data
    ) {

        const msg =
            document.createElement('div');

        msg.className =
            'bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-800 self-start max-w-xs';


        const username =
            document.createElement('span');

        username.className =
            'text-' +
            (
                data.user?.color ||
                'gray'
            ) +
            '-600';

        username.textContent =
            data.user?.username ||
            'Unknown';


        msg.appendChild(
            username
        );

        msg.appendChild(
            document.createElement('br')
        );


        const text =
            document.createElement('span');

        text.innerHTML =
            autolink(
                data.message || ''
            );

        msg.appendChild(
            text
        );


        container.appendChild(
            msg
        );

        container.scrollTop =
            container.scrollHeight;

        return msg;
    }


    function renderPost(
        post,
        options
    ) {

        options = options || {};

        const currentUserId =
            options.currentUserId;

        const isAdmin =
            options.isAdmin ||
            false;

        const isSubscriber =
            options.isSubscriber ||
            false;

        const myColor =
            options.myColor ||
            'gray';

        const row =
            document.createElement('div');

        const author =
            post.author ||
            {};

        const authorId =
            author.id;

        const authorName =
            author.username ||
            'Deleted user';

        const authorColor =
            author.color ||
            'gray';

        const isMine =
            Number(authorId) ===
            Number(currentUserId);

        row.className =
            'flex items-start gap-2' +
            (
                isMine
                    ? ' justify-end'
                    : ''
            );

        row.dataset.postId =
            post.id;

        row.dataset.authorId =
            authorId || '';

        row.dataset.attachments =
            JSON.stringify(
                post.attachments || []
            );


        function makeAvatar() {

            return createAvatar({
                avatarUrl:
                    author.avatar,

                username:
                    authorName,

                color:
                    authorColor,

                size:
                    '9'
            });
        }


        if (!isMine) {
            row.appendChild(
                makeAvatar()
            );
        }


        const canManage =
            isAdmin ||
            isMine;


        const bubble =
            document.createElement('div');

        bubble.className =
            'chat-message-bubble px-3 py-2 rounded-lg text-sm max-w-xs break-words ' +
            (
                canManage
                    ? 'cursor-pointer '
                    : ''
            ) +
            (
                isMine
                    ? `bg-${authorColor}-100 text-gray-800`
                    : 'bg-gray-100 text-gray-800'
            );


        if (!isMine) {

            const head =
                document.createElement('div');

            head.className =
                `text-xs font-medium text-${authorColor}-500 mb-1 flex items-center justify-between gap-2`;

            const nameSpan =
                document.createElement('span');

            nameSpan.textContent =
                authorName;

            const dateSpan =
                document.createElement('span');

            dateSpan.className =
                'text-xs text-gray-400 font-normal';

            dateSpan.textContent =
                post.created_at || '';

            head.appendChild(
                nameSpan
            );

            head.appendChild(
                dateSpan
            );

            bubble.appendChild(
                head
            );

        } else {

            const dateDiv =
                document.createElement('div');

            dateDiv.className =
                'text-xs text-gray-400 mb-1 text-right';

            dateDiv.textContent =
                post.created_at || '';

            bubble.appendChild(
                dateDiv
            );
        }


        const contentDiv =
            document.createElement('div');

        contentDiv.className =
            'post-content whitespace-pre-wrap break-words' +
            (
                post.content
                    ? ''
                    : ' hidden'
            );

        contentDiv.innerHTML =
            autolink(
                post.content || ''
            );

        bubble.appendChild(
            contentDiv
        );


        const attDiv =
            document.createElement('div');

        attDiv.className =
            'post-attachments flex flex-col gap-1.5' +
            (
                post.content &&
                post.attachments &&
                post.attachments.length
                    ? ' mt-2'
                    : ''
            );

        attDiv.innerHTML =
            renderAttachmentsHTML(
                post.attachments
            );

        bubble.appendChild(
            attDiv
        );


        const footerRow =
            document.createElement('div');

        footerRow.className =
            'flex items-center justify-between gap-2 mt-1';


        const likeRow =
            document.createElement('div');

        likeRow.className =
            'flex items-center gap-1';


        const likeBtn =
            document.createElement('button');

        likeBtn.type =
            'button';

        likeBtn.className =
            'like-btn flex items-center gap-1 text-xs text-gray-400' +
            (
                isSubscriber
                    ? ' hover:opacity-75'
                    : ' opacity-50 cursor-not-allowed'
            );

        likeBtn.dataset.postId =
            post.id;

        likeBtn.dataset.liked =
            post.liked
                ? '1'
                : '0';

        if (!isSubscriber) {
            likeBtn.disabled = true;
        }


        const likeIcon =
            document.createElement('span');

        likeIcon.className =
            'like-icon';

        likeIcon.innerHTML =
            post.liked
                ? '&#9829;'
                : '&#9825;';


        const likeCount =
            document.createElement('span');

        likeCount.className =
            'like-count';

        likeCount.textContent =
            post.like_count ??
            post.likes_count ??
            0;


        likeBtn.appendChild(
            likeIcon
        );

        likeBtn.appendChild(
            likeCount
        );

        likeRow.appendChild(
            likeBtn
        );

        footerRow.appendChild(
            likeRow
        );

        bubble.appendChild(
            footerRow
        );


        row.appendChild(
            bubble
        );


        if (isMine) {
            row.appendChild(
                makeAvatar()
            );
        }


        if (
            typeof options.wireLikeButton ===
            'function'
        ) {
            options.wireLikeButton(
                likeBtn
            );
        }

        return row;
    }


    function appendPost(
        container,
        post,
        options
    ) {

        const element =
            renderPost(
                post,
                options
            );

        container.appendChild(
            element
        );

        return element;
    }


    function updatePost(
        postId,
        data
    ) {

        const card =
            document.querySelector(
                `[data-post-id="${CSS.escape(String(postId))}"]`
            );

        if (!card) {
            return false;
        }


        card.dataset.attachments =
            JSON.stringify(
                data.attachments || []
            );


        const contentEl =
            card.querySelector(
                '.post-content'
            );

        if (contentEl) {

            if (data.content) {

                contentEl.innerHTML =
                    autolink(
                        data.content
                    );

                contentEl.classList.remove(
                    'hidden'
                );

            } else {

                contentEl.innerHTML =
                    '';

                contentEl.classList.add(
                    'hidden'
                );
            }
        }


        const attEl =
            card.querySelector(
                '.post-attachments'
            );

        if (attEl) {

            attEl.innerHTML =
                renderAttachmentsHTML(
                    data.attachments
                );

            if (
                data.content &&
                data.attachments &&
                data.attachments.length
            ) {

                attEl.classList.add(
                    'mt-2'
                );

            } else {

                attEl.classList.remove(
                    'mt-2'
                );
            }
        }

        return true;
    }


    function deletePost(
        postId
    ) {

        const card =
            document.querySelector(
                `[data-post-id="${CSS.escape(String(postId))}"]`
            );

        if (!card) {
            return false;
        }

        card.remove();

        return true;
    }


    window.MakaMessages = {

        escapeHtml,
        autolink,

        createAvatar,

        renderAttachmentsHTML,

        renderMessage,
        appendMessage,
        updateMessage,
        deleteMessage,

        addSystemMessage,

        appendLobbyMessage,

        renderPost,
        appendPost,
        updatePost,
        deletePost
    };

})();