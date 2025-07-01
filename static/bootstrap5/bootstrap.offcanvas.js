/*!
  * Bootstrap v5.1.3 (https://getbootstrap.com/)
  * Copyright 2011-2021 The Bootstrap Authors (https://github.com/twbs/bootstrap/graphs/contributors)
  * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
  */
!function (t, e) {
    "object" == typeof exports && "undefined" != typeof module ? module.exports = e() : "function" == typeof define && define.amd ? define(e) : (t = "undefined" != typeof globalThis ? globalThis : t || self).bootstrap = e()
}(this, (function () {
    "use strict";
 class Hi extends B {
        constructor(t, e) {
            super(t), this._config = this._getConfig(e), this._dialog = V.findOne(".modal-dialog", this._element), this._backdrop = this._initializeBackDrop(), this._focustrap = this._initializeFocusTrap(), this._isShown = !1, this._ignoreBackdropClick = !1, this._isTransitioning = !1, this._scrollBar = new fi
        }

        static get Default() {
            return Ci
        }

        static get NAME() {
            return Ti
        }

        toggle(t) {
            return this._isShown ? this.hide() : this.show(t)
        }

        show(t) {
            this._isShown || this._isTransitioning || j.trigger(this._element, xi, {relatedTarget: t}).defaultPrevented || (this._isShown = !0, this._isAnimated() && (this._isTransitioning = !0), this._scrollBar.hide(), document.body.classList.add(Pi), this._adjustDialog(), this._setEscapeEvent(), this._setResizeEvent(), j.on(this._dialog, Ii, (() => {
                j.one(this._element, "mouseup.dismiss.bs.modal", (t => {
                    t.target === this._element && (this._ignoreBackdropClick = !0)
                }))
            })), this._showBackdrop((() => this._showElement(t))))
        }

        hide() {
            if (!this._isShown || this._isTransitioning) return;
            if (j.trigger(this._element, "hide.bs.modal").defaultPrevented) return;
            this._isShown = !1;
            const t = this._isAnimated();
            t && (this._isTransitioning = !0), this._setEscapeEvent(), this._setResizeEvent(), this._focustrap.deactivate(), this._element.classList.remove(ji), j.off(this._element, Si), j.off(this._dialog, Ii), this._queueCallback((() => this._hideModal()), this._element, t)
        }

        dispose() {
            [window, this._dialog].forEach((t => j.off(t, ".bs.modal"))), this._backdrop.dispose(), this._focustrap.deactivate(), super.dispose()
        }

        handleUpdate() {
            this._adjustDialog()
        }

        _initializeBackDrop() {
            return new bi({isVisible: Boolean(this._config.backdrop), isAnimated: this._isAnimated()})
        }

        _initializeFocusTrap() {
            return new Ai({trapElement: this._element})
        }

        _getConfig(t) {
            return t = {...Ci, ...U.getDataAttributes(this._element), ..."object" == typeof t ? t : {}}, a(Ti, t, ki), t
        }

        _showElement(t) {
            const e = this._isAnimated(), i = V.findOne(".modal-body", this._dialog);
            this._element.parentNode && this._element.parentNode.nodeType === Node.ELEMENT_NODE || document.body.append(this._element), this._element.style.display = "block", this._element.removeAttribute("aria-hidden"), this._element.setAttribute("aria-modal", !0), this._element.setAttribute("role", "dialog"), this._element.scrollTop = 0, i && (i.scrollTop = 0), e && u(this._element), this._element.classList.add(ji), this._queueCallback((() => {
                this._config.focus && this._focustrap.activate(), this._isTransitioning = !1, j.trigger(this._element, "shown.bs.modal", {relatedTarget: t})
            }), this._dialog, e)
        }

        _setEscapeEvent() {
            this._isShown ? j.on(this._element, Ni, (t => {
                this._config.keyboard && t.key === Oi ? (t.preventDefault(), this.hide()) : this._config.keyboard || t.key !== Oi || this._triggerBackdropTransition()
            })) : j.off(this._element, Ni)
        }

        _setResizeEvent() {
            this._isShown ? j.on(window, Di, (() => this._adjustDialog())) : j.off(window, Di)
        }

        _hideModal() {
            this._element.style.display = "none", this._element.setAttribute("aria-hidden", !0), this._element.removeAttribute("aria-modal"), this._element.removeAttribute("role"), this._isTransitioning = !1, this._backdrop.hide((() => {
                document.body.classList.remove(Pi), this._resetAdjustments(), this._scrollBar.reset(), j.trigger(this._element, Li)
            }))
        }

        _showBackdrop(t) {
            j.on(this._element, Si, (t => {
                this._ignoreBackdropClick ? this._ignoreBackdropClick = !1 : t.target === t.currentTarget && (!0 === this._config.backdrop ? this.hide() : "static" === this._config.backdrop && this._triggerBackdropTransition())
            })), this._backdrop.show(t)
        }

        _isAnimated() {
            return this._element.classList.contains("fade")
        }

        _triggerBackdropTransition() {
            if (j.trigger(this._element, "hidePrevented.bs.modal").defaultPrevented) return;
            const {classList: t, scrollHeight: e, style: i} = this._element, n = e > document.documentElement.clientHeight;
            !n && "hidden" === i.overflowY || t.contains(Mi) || (n || (i.overflowY = "hidden"), t.add(Mi), this._queueCallback((() => {
                t.remove(Mi), n || this._queueCallback((() => {
                    i.overflowY = ""
                }), this._dialog)
            }), this._dialog), this._element.focus())
        }

        _adjustDialog() {
            const t = this._element.scrollHeight > document.documentElement.clientHeight, e = this._scrollBar.getWidth(), i = e > 0;
            (!i && t && !m() || i && !t && m()) && (this._element.style.paddingLeft = `${e}px`), (i && !t && !m() || !i && t && m()) && (this._element.style.paddingRight = `${e}px`)
        }

        _resetAdjustments() {
            this._element.style.paddingLeft = "", this._element.style.paddingRight = ""
        }

        static jQueryInterface(t, e) {
            return this.each((function () {
                const i = Hi.getOrCreateInstance(this, t);
                if ("string" == typeof t) {
                    if (void 0 === i[t]) throw new TypeError(`No method named "${t}"`);
                    i[t](e)
                }
            }))
        }
    }

    j.on(document, "click.bs.modal.data-api", '[data-bs-toggle="modal"]', (function (t) {
        const e = n(this);
        ["A", "AREA"].includes(this.tagName) && t.preventDefault(), j.one(e, xi, (t => {
            t.defaultPrevented || j.one(e, Li, (() => {
                l(this) && this.focus()
            }))
        }));
        const i = V.findOne(".modal.show");
        i && Hi.getInstance(i).hide(), Hi.getOrCreateInstance(e).toggle(this)
    })), R(Hi), g(Hi);
    const Bi = "offcanvas", Ri = {backdrop: !0, keyboard: !0, scroll: !1}, Wi = {backdrop: "boolean", keyboard: "boolean", scroll: "boolean"}, $i = "show", zi = ".offcanvas.show", qi = "hidden.bs.offcanvas";

    class Fi extends B {
        constructor(t, e) {
            super(t), this._config = this._getConfig(e), this._isShown = !1, this._backdrop = this._initializeBackDrop(), this._focustrap = this._initializeFocusTrap(), this._addEventListeners()
        }

        static get NAME() {
            return Bi
        }

        static get Default() {
            return Ri
        }

        toggle(t) {
            return this._isShown ? this.hide() : this.show(t)
        }

        show(t) {
            this._isShown || j.trigger(this._element, "show.bs.offcanvas", {relatedTarget: t}).defaultPrevented || (this._isShown = !0, this._element.style.visibility = "visible", this._backdrop.show(), this._config.scroll || (new fi).hide(), this._element.removeAttribute("aria-hidden"), this._element.setAttribute("aria-modal", !0), this._element.setAttribute("role", "dialog"), this._element.classList.add($i), this._queueCallback((() => {
                this._config.scroll || this._focustrap.activate(), j.trigger(this._element, "shown.bs.offcanvas", {relatedTarget: t})
            }), this._element, !0))
        }

        hide() {
            this._isShown && (j.trigger(this._element, "hide.bs.offcanvas").defaultPrevented || (this._focustrap.deactivate(), this._element.blur(), this._isShown = !1, this._element.classList.remove($i), this._backdrop.hide(), this._queueCallback((() => {
                this._element.setAttribute("aria-hidden", !0), this._element.removeAttribute("aria-modal"), this._element.removeAttribute("role"), this._element.style.visibility = "hidden", this._config.scroll || (new fi).reset(), j.trigger(this._element, qi)
            }), this._element, !0)))
        }

        dispose() {
            this._backdrop.dispose(), this._focustrap.deactivate(), super.dispose()
        }

        _getConfig(t) {
            return t = {...Ri, ...U.getDataAttributes(this._element), ..."object" == typeof t ? t : {}}, a(Bi, t, Wi), t
        }

        _initializeBackDrop() {
            return new bi({className: "offcanvas-backdrop", isVisible: this._config.backdrop, isAnimated: !0, rootElement: this._element.parentNode, clickCallback: () => this.hide()})
        }

        _initializeFocusTrap() {
            return new Ai({trapElement: this._element})
        }

        _addEventListeners() {
            j.on(this._element, "keydown.dismiss.bs.offcanvas", (t => {
                this._config.keyboard && "Escape" === t.key && this.hide()
            }))
        }

        static jQueryInterface(t) {
            return this.each((function () {
                const e = Fi.getOrCreateInstance(this, t);
                if ("string" == typeof t) {
                    if (void 0 === e[t] || t.startsWith("_") || "constructor" === t) throw new TypeError(`No method named "${t}"`);
                    e[t](this)
                }
            }))
        }
    }

    j.on(document, "click.bs.offcanvas.data-api", '[data-bs-toggle="offcanvas"]', (function (t) {
        const e = n(this);
        if (["A", "AREA"].includes(this.tagName) && t.preventDefault(), c(this)) return;
        j.one(e, qi, (() => {
            l(this) && this.focus()
        }));
        const i = V.findOne(zi);
        i && i !== e && Fi.getInstance(i).hide(), Fi.getOrCreateInstance(e).toggle(this)
    })), j.on(window, "load.bs.offcanvas.data-api", (() => V.find(zi).forEach((t => Fi.getOrCreateInstance(t).show())))), R(Fi), g(Fi);
    const Ui = new Set(["background", "cite", "href", "itemtype", "longdesc", "poster", "src", "xlink:href"]), Vi = /^(?:(?:https?|mailto|ftp|tel|file|sms):|[^#&/:?]*(?:[#/?]|$))/i, Ki = /^data:(?:image\/(?:bmp|gif|jpeg|jpg|png|tiff|webp)|video\/(?:mpeg|mp4|ogg|webm)|audio\/(?:mp3|oga|ogg|opus));base64,[\d+/a-z]+=*$/i, Xi = (t, e) => {
        const i = t.nodeName.toLowerCase();
        if (e.includes(i)) return !Ui.has(i) || Boolean(Vi.test(t.nodeValue) || Ki.test(t.nodeValue));
        const n = e.filter((t => t instanceof RegExp));
        for (let t = 0, e = n.length; t < e; t++) if (n[t].test(i)) return !0;
        return !1
    };


    return {Offcanvas: Fi}
}));