// One lifecycle across Streamlit reruns. Only presentation and accessibility;
// native widgets continue to own uploads, recording, selection and submission.
(() => {
    if (window.researchDashboard) {
        window.researchDashboard.refresh();
        return;
    }
    let scheduled = false;
    let composer;
    let lastUser = '';
    let lastAnswer = '';
    let lastStep = '';
    let lastReadyToken = '';
    let followAnswer = true;
    const root = document.documentElement;
    const visible = el => el && el.getClientRects().length && el.checkVisibility();
    function reveal(el, block = 'end') {
        if (visible(el)) el.scrollIntoView({ block, behavior: 'instant' });
    }
    function update() {
        scheduled = false;
        const nextComposer = document.querySelector('.st-key-chat_composer_shell');
        if (nextComposer !== composer) {
            if (composer) resizeObserver.unobserve(composer);
            composer = nextComposer;
            if (composer) resizeObserver.observe(composer);
        }
        const height = visible(composer) ? Math.ceil(composer.getBoundingClientRect().height) : 0;
        const reserve = `${height + 32}px`;
        if (root.style.getPropertyValue('--composer-reserve') !== reserve) {
            root.style.setProperty('--composer-reserve', reserve);
        }
        const viewport = window.visualViewport;
        // Mobile keyboards can resize the visual viewport without changing dvh.
        const inset = viewport && viewport.scale === 1
            ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
        root.style.setProperty('--keyboard-inset', `${Math.round(inset)}px`);
        const feed = document.querySelector('.st-key-chat_transcript');
        const users = feed?.querySelectorAll('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])');
        const user = users?.length ? `${users.length}:${users[users.length - 1].textContent}` : '';
        const messages = feed?.querySelectorAll('[data-testid="stChatMessage"]');
        const newest = messages?.length ? messages[messages.length - 1] : null;
        const answer = newest?.textContent || '';
        if (user && user !== lastUser) followAnswer = true;
        if (visible(feed) && followAnswer && user && (user !== lastUser || answer !== lastAnswer)) {
            reveal(newest);
            lastUser = user;
            lastAnswer = answer;
        }
        const marker = document.querySelector('.tour-marker');
        const step = marker?.className.match(/tour-step-(\d)/)?.[1] || '';
        if (step !== lastStep && lastStep) {
            if (step === '1') {
                const rail = document.querySelector('.st-key-document_rail');
                if (rail) rail.scrollTop = 0;
                reveal(rail, 'start');
            } else if (step === '3') {
                reveal(document.querySelector('.st-key-active_document_selector'), 'center');
            } else if (step === '4') {
                reveal(document.querySelector('.chat-workspace__header'), 'start');
            }
        }
        lastStep = step;
        const readyToken = document.querySelector('.auto-focus-composer')?.dataset.readyToken || '';
        if (readyToken && readyToken !== lastReadyToken && composer) {
            reveal(document.querySelector('.chat-workspace__header'), 'start');
            reveal(composer, 'end');
            lastReadyToken = readyToken;
        }
        for (const [testid, label] of [
            ['stChatInputSubmitButton', 'إرسال الرسالة'],
            ['stChatInputMicButton', 'بدء التسجيل الصوتي'],
        ]) {
            const button = document.querySelector(`[data-testid="${testid}"]`);
            if (button && (testid !== 'stChatInputMicButton' || button.getAttribute('aria-label') === 'Start recording')) {
                if (button.getAttribute('aria-label') !== label) button.setAttribute('aria-label', label);
            }
        }
        const uploadButton = document.querySelector('.st-key-document_rail [data-testid="stFileUploaderDropzone"] button');
        const uploadLabel = uploadButton?.querySelector('[data-testid="stMarkdownContainer"] p');
        if (uploadLabel && uploadLabel.textContent !== 'رفع الملفات') uploadLabel.textContent = 'رفع الملفات';
        if (uploadButton && uploadButton.getAttribute('aria-label') !== 'رفع ملفات PDF') {
            uploadButton.setAttribute('aria-label', 'رفع ملفات PDF');
        }
    }
    function refresh() {
        if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
    }
    const resizeObserver = new ResizeObserver(refresh);
    const observer = new MutationObserver(refresh);
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    window.addEventListener('resize', refresh, { passive: true });
    window.visualViewport?.addEventListener('resize', refresh, { passive: true });
    window.visualViewport?.addEventListener('scroll', refresh, { passive: true });
    document.addEventListener('wheel', event => {
        if (event.deltaY < 0 && !event.target.closest('.st-key-document_rail')) followAnswer = false;
    }, { passive: true });
    document.addEventListener('touchstart', event => {
        if (!event.target.closest('.st-key-chat_composer_shell')) followAnswer = false;
    }, { passive: true });
    window.researchDashboard = { refresh };
    refresh();
})();
