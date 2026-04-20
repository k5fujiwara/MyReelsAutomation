function fitTextElement(element, minSizePx) {
    const computed = window.getComputedStyle(element);
    const originalSize = parseFloat(computed.fontSize);
    const lineHeight = parseFloat(computed.lineHeight);
    const lineLimit = parseInt(element.dataset.fitLines || "0", 10);

    if (!originalSize || !lineHeight || !lineLimit) {
        return;
    }

    element.style.maxHeight = `${lineHeight * lineLimit}px`;
    element.style.overflow = "hidden";

    let size = originalSize;
    let guard = 0;
    while (guard < 50 && size > minSizePx) {
        if (element.scrollHeight <= element.clientHeight && element.scrollWidth <= element.clientWidth) {
            break;
        }
        size -= 2;
        element.style.fontSize = `${size}px`;
        guard += 1;
    }

    element.style.maxHeight = "none";
    element.style.overflow = "visible";
}

window.addEventListener("load", () => {
    document.querySelectorAll(".fit-text").forEach((element) => {
        const minSize = parseFloat(element.dataset.minSize || "28");
        fitTextElement(element, minSize);
    });
});
