/*!
 * bootstrap-star-rating v4.1.0
 * http://plugins.krajee.com/star-rating
 *
 * Author: Kartik Visweswaran
 * Copyright: 2013 - 2021, Kartik Visweswaran, Krajee.com
 *
 * Licensed under the BSD 3-Clause
 * https://github.com/kartik-v/bootstrap-star-rating/blob/master/LICENSE.md
 */
(function (factory) {
    'use strict';
    //noinspection JSUnresolvedVariable
    if (typeof define === 'function' && define.amd) { // jshint ignore:line
        // AMD. Register as an anonymous module.
        define(['jquery'], factory); // jshint ignore:line
    } else { // noinspection JSUnresolvedVariable
        if (typeof module === 'object' && module.exports) { // jshint ignore:line
            // Node/CommonJS
            // noinspection JSUnresolvedVariable
            module.exports = factory(require('jquery')); // jshint ignore:line
        } else {
            // Browser globals
            factory(window.jQuery);
        }
    }
}(function ($) {
    'use strict';

    $.fn.ratingLocales = {};
    $.fn.ratingThemes = {};

    var $h, Rating;

    // global helper methods and constants
    $h = {
        NAMESPACE: '.rating',
        DEFAULT_MIN: 0,
        DEFAULT_MAX: 5,
        DEFAULT_STEP: 0.5,
        isEmpty: function (value, trim) {
            return value === null || value === undefined || value.length === 0 || (trim && $.trim(value) === '');
        },
        getCss: function (condition, css) {
            return condition ? ' ' + css : '';
        },
        addCss: function ($el, css) {
            $el.removeClass(css).addClass(css);
        },
        getDecimalPlaces: function (num) {
            var m = ('' + num).match(/(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/);
            return !m ? 0 : Math.max(0, (m[1] ? m[1].length : 0) - (m[2] ? +m[2] : 0));
        },
        applyPrecision: function (val, precision) {
            return parseFloat(val.toFixed(precision));
        },
        handler: function ($el, event, callback, skipOff, skipNS) {
            var ev = skipNS ? event : event.split(' ').join($h.NAMESPACE + ' ') + $h.NAMESPACE;
            if (!skipOff) {
                $el.off(ev);
            }
            $el.on(ev, function (e) {
                var cb = $.proxy(callback, self);
                cb(e);
            });
        }
    };

    // rating constructor
    Rating = function (element, options) {
        var self = this;
        self.$element = $(element);
        self._init(options);
    };
    Rating.prototype = {
        constructor: Rating,
        _parseAttr: function (vattr, options) {
            var self = this, $el = self.$element, elType = $el.attr('type'), finalVal, val, chk, out;
            if (elType === 'range' || elType === 'number') {
                val = options[vattr] || $el.data(vattr) || $el.attr(vattr);
                switch (vattr) {
                    case 'min':
                        chk = $h.DEFAULT_MIN;
                        break;
                    case 'max':
                        chk = $h.DEFAULT_MAX;
                        break;
                    default:
                        chk = $h.DEFAULT_STEP;
                }
                finalVal = $h.isEmpty(val) ? chk : val;
                out = parseFloat(finalVal);
            } else {
                out = parseFloat(options[vattr]);
            }
            return isNaN(out) ? chk : out;
        },
        _parseValue: function (val) {
            var self = this, v = parseFloat(val);
            if (isNaN(v)) {
                v = self.clearValue;
            }
            return (self.zeroAsNull && (v === 0 || v === '0') ? null : v);
        },
        _setDefault: function (key, val) {
            var self = this;
            if ($h.isEmpty(self[key])) {
                self[key] = val;
            }
        },
        _initSlider: function (options) {
            var self = this, v = self.$element.val();
            self.initialValue = $h.isEmpty(v) ? 0 : v;
            self._setDefault('min', self._parseAttr('min', options));
            self._setDefault('max', self._parseAttr('max', options));
            self._setDefault('step', self._parseAttr('step', options));
            if (isNaN(self.min) || $h.isEmpty(self.min)) {
                self.min = $h.DEFAULT_MIN;
            }
            if (isNaN(self.max) || $h.isEmpty(self.max)) {
                self.max = $h.DEFAULT_MAX;
            }
            if (isNaN(self.step) || $h.isEmpty(self.step) || self.step === 0) {
                self.step = $h.DEFAULT_STEP;
            }
            self.diff = self.max - self.min;
            self._setDefault('minThreshold', self.min);
            if (self.minThreshold < self.min) {
                self.minThreshold = self.min;
            }
            if (self.minThreshold > self.max) {
                self.minThreshold = self.max;
            }
        },
        _initHighlight: function (v) {
            var self = this, w, cap = self._getCaption();
            if (!v) {
                v = self.$element.val();
            }
            w = self.getWidthFromValue(v) + '%';
            self.$filledStars.width(w);
            self.cache = {caption: cap, width: w, val: v};
        },
        _getContainerCss: function () {
            var self = this;
            return 'rating-container' +
                $h.getCss(self.theme, 'theme-' + self.theme) +
                $h.getCss(self.rtl, 'rating-rtl') +
                $h.getCss(self.size, 'rating-' + self.size) +
                $h.getCss(self.animate, 'rating-animate') +
                $h.getCss(self.disabled || self.readonly, 'rating-disabled') +
                $h.getCss(self.containerClass, self.containerClass) +
                (self.displayOnly ? ' is-display-only' : '');

        },
        _checkDisabled: function () {
            var self = this, $el = self.$element, opts = self.options;
            self.disabled = opts.disabled === undefined ? $el.attr('disabled') || false : opts.disabled;
            self.readonly = opts.readonly === undefined ? $el.attr('readonly') || false : opts.readonly;
            self.inactive = (self.disabled || self.readonly);
            $el.attr({disabled: self.disabled, readonly: self.readonly});
        },
        _addContent: function (type, content) {
            var self = this, $container = self.$container, isClear = type === 'clear';
            if (self.rtl) {
                return isClear ? $container.append(content) : $container.prepend(content);
            } else {
                return isClear ? $container.prepend(content) : $container.append(content);
            }
        },
        _generateRating: function () {
            var self = this, $el = self.$element, $rating, $container, w;
            $container = self.$container = $(document.createElement('div')).insertBefore($el);
            $h.addCss($container, self._getContainerCss());
            self.$rating = $rating = $(document.createElement('div')).attr('class', 'rating-stars').appendTo($container)
                .append(self._getStars('empty')).append(self._getStars('filled'));
            if (self.keyboardEnabled) {
                self.$rating.attr('tabindex', self.tabindex);
            }
            self.$emptyStars = $rating.find('.empty-stars');
            self.$filledStars = $rating.find('.filled-stars');
            self._renderCaption();
            self._renderClear();
            self._initHighlight();
            self._initStarTitles();
            var i = 1;
            if (self.rtl) {
                w = Math.max(self.$emptyStars.outerWidth(), self.$filledStars.outerWidth());
                self.$emptyStars.width(w);
            }
            $container.insertBefore($el);
        },
        _getCaption: function () {
            var self = this;
            return self.$caption && self.$caption.length ? self.$caption.html() : self.defaultCaption;
        },
        _setCaption: function (content) {
            var self = this;
            if (self.$caption && self.$caption.length) {
                self.$caption.html(content);
            }
        },
        _renderCaption: function () {
            var self = this, val = self.$element.val(), html, $cap = self.captionElement ? $(self.captionElement) : '';
            if (!self.showCaption) {
                return;
            }
            html = self.fetchCaption(val);
            if ($cap && $cap.length) {
                $h.addCss($cap, 'caption');
                $cap.html(html);
                self.$caption = $cap;
                return;
            }
            self._addContent('caption', '<div class="caption">' + html + '</div>');
            self.$caption = self.$container.find('.caption');
        },
        _renderClear: function () {
            var self = this, css, $clr = self.clearElement ? $(self.clearElement) : '';
            if (!self.showClear) {
                return;
            }
            css = self._getClearClass();
            if ($clr.length) {
                $h.addCss($clr, css);
                $clr.attr({'title': self.clearButtonTitle}).html(self.clearButton);
                self.$clear = $clr;
                return;
            }
            self._addContent('clear',
                '<div class="' + css + '" title="' + self.clearButtonTitle + '">' + self.clearButton + '</div>');
            self.$clear = self.$container.find('.' + self.clearButtonBaseClass);
        },
        _getClearClass: function () {
            var self = this;
            return self.clearButtonBaseClass + ' ' + (self.inactive ? '' : self.clearButtonActiveClass);
        },
        _toggleHover: function (out) {
            var self = this, w, width, caption;
            if (!out) {
                return;
            }
            if (self.hoverChangeStars) {
                w = self.getWidthFromValue(self.clearValue);
                width = out.val <= self.clearValue ? w + '%' : out.width;
                self.$filledStars.css('width', width);
            }
            if (self.hoverChangeCaption) {
                caption = out.val <= self.clearValue ? self.fetchCaption(self.clearValue) : out.caption;
                if (caption) {
                    self._setCaption(caption + '');
                }
            }
        },
        _init: function (options) {
            var self = this, $el = self.$element.attr('tabindex', -1).addClass('rating-input'), v,
                m = self.minThreshold;
            self.options = options;
            $.each(options, function (key, value) {
                self[key] = value;
            });
            if (self.rtl || $el.attr('dir') === 'rtl') {
                self.rtl = true;
                $el.attr('dir', 'rtl');
            }
            self.starClicked = false;
            self.clearClicked = false;
            self._initSlider(options);
            self._checkDisabled();
            if (self.displayOnly) {
                self.inactive = true;
                self.showClear = false;
                self.hoverEnabled = false;
                self.hoverChangeCaption = false;
                self.hoverChangeStars = false;
            }
            self._generateRating();
            self._initEvents();
            self._listen();
            if (!$h.isEmpty(m) && ($h.isEmpty($el.val()) || $el.val() < m)) {
                $el.val(m);
            }
            v = self._parseValue($el.val());
            $el.val(v);
            return $el.removeClass('rating-loading');
        },
        _initCaptionTitle: function () {
            var self = this, caption;
            caption = self.fetchCaption(self.$element.val());
            self.$rating.attr('title', $(caption).text());
        },
        _trigChange: function (params) {
            var self = this;
            self._initStarTitles();
            self.$element.trigger('change').trigger('rating:change', params);
        },
        _initEvents: function () {
            var self = this;
            self.events = {
                _getTouchPosition: function (e) {
                    var pageX = $h.isEmpty(e.pageX) ? e.originalEvent.touches[0].pageX : e.pageX;
                    return pageX - self.$rating.offset().left;
                },
                _listenClick: function (e, callback) {
                    e.stopPropagation();
                    e.preventDefault();
                    if (e.handled !== true) {
                        callback(e);
                        e.handled = true;
                    } else {
                        return false;
                    }
                },
                _noMouseAction: function (e) {
                    return !self.mouseEnabled || !self.hoverEnabled || self.inactive || (e && e.isDefaultPrevented());
                },
                initTouch: function (e) {
                    //noinspection JSUnresolvedVariable
                    var ev, touches, pos, out, caption, w, width, params, clrVal = self.clearValue || 0,
                        isTouchCapable = 'ontouchstart' in window ||
                            (window.DocumentTouch && document instanceof window.DocumentTouch);
                    if (!isTouchCapable || self.inactive) {
                        return;
                    }
                    ev = e.originalEvent;
                    //noinspection JSUnresolvedVariable
                    touches = !$h.isEmpty(ev.touches) ? ev.touches : ev.changedTouches;
                    pos = self.events._getTouchPosition(touches[0]);
                    if (e.type === 'touchend') {
                        self._setStars(pos);
                        params = [self.$element.val(), self._getCaption()];
                        self._trigChange(params);
                        self.starClicked = true;
                    } else {
                        out = self.calculate(pos);
                        caption = out.val <= clrVal ? self.fetchCaption(clrVal) : out.caption;
                        w = self.getWidthFromValue(clrVal);
                        width = out.val <= clrVal ? w + '%' : out.width;
                        self._setCaption(caption);
                        self.$filledStars.css('width', width);
                    }
                },
                starClick: function (e) {
                    var pos, params;
                    self.events._listenClick(e, function (ev) {
                        if (self.inactive) {
                            return false;
                        }
                        pos = self.events._getTouchPosition(ev);
                        self._setStars(pos);
                        params = [self.$element.val(), self._getCaption()];
                        self._trigChange(params);
                        self.starClicked = true;
                    });
                },
                clearClick: function (e) {
                    self.events._listenClick(e, function () {
                        if (!self.inactive) {
                            self.clear();
                            self.clearClicked = true;
                        }
                    });
                },
                starMouseMove: function (e) {
                    var pos, out;
                    if (self.events._noMouseAction(e)) {
                        return;
                    }
                    self.starClicked = false;
                    pos = self.events._getTouchPosition(e);
                    out = self.calculate(pos);
                    self._toggleHover(out);
                    self.$element.trigger('rating:hover', [out.val, out.caption, 'stars']);
                },
                starMouseLeave: function (e) {
                    var out;
                    if (self.events._noMouseAction(e) || self.starClicked) {
                        return;
                    }
                    out = self.cache;
                    self._toggleHover(out);
                    self.$element.trigger('rating:hoverleave', ['stars']);
                },
                clearMouseMove: function (e) {
                    var caption, val, width, out;
                    if (self.events._noMouseAction(e) || !self.hoverOnClear) {
                        return;
                    }
                    self.clearClicked = false;
                    caption = '<span class="' + self.clearCaptionClass + '">' + self.clearCaption + '</span>';
                    val = self.clearValue;
                    width = self.getWidthFromValue(val) || 0;
                    out = {caption: caption, width: width, val: val};
                    self._toggleHover(out);
                    self.$element.trigger('rating:hover', [val, caption, 'clear']);
                },
                clearMouseLeave: function (e) {
                    var out;
                    if (self.events._noMouseAction(e) || self.clearClicked || !self.hoverOnClear) {
                        return;
                    }
                    out = self.cache;
                    self._toggleHover(out);
                    self.$element.trigger('rating:hoverleave', ['clear']);
                },
                resetForm: function (e) {
                    if (e && e.isDefaultPrevented()) {
                        return;
                    }
                    if (!self.inactive) {
                        self.reset();
                    }
                },
                focus: function (e) {
                    self.$rating.focus();
                    self.$element.trigger('rating:focus');
                },
                blur: function (e) {
                    self.$element.trigger('rating:blur');
                },
                keydown: function (e) {
                    if (self.inactive || !self.keyboardEnabled) {
                        return;
                    }
                    var $el = self.$element, v = $el.val(), isUpdated = false, step = parseFloat(self.step),
                        precision = $h.getDecimalPlaces(step), upKey = self.rtl ? 37 : 39, dnKey = self.rtl ? 39 : 37,
                        val = v ? parseFloat(v) : 0, key = parseInt(e.which || e.keyCode || 0, 10);
                    if (key === upKey && val < self.max) { // key right (increase)
                        val += step;
                        isUpdated = true;
                    }
                    if (key === dnKey && val > self.minThreshold) { // key left (decrease)
                        val -= step;
                        isUpdated = true
                    }
                    if (isUpdated) {
                        val = $h.applyPrecision(val, precision);
                        $el.val(val);
                        self._trigChange([val, self._getCaption()])
                        self.showStars($el.val());
                        self.$rating.focus();
                    }
                    if (key === 37 || key === 39) {
                        $el.trigger('rating:keydown', [val, self._getCaption()]);
                    }

                }
            };
        },
        _listen: function () {
            var self = this, $el = self.$element, $form = $el.closest('form'), $rating = self.$rating,
                $clear = self.$clear, events = self.events, ns = $h.NAMESPACE,
                mouseEvents = 'mousenter' + ns + ' mouseleave' + ns, $stars = self.$rating.find('.star');
            $h.handler($rating, 'touchstart touchmove touchend', events.initTouch);
            $h.handler($rating, 'click touchstart', events.starClick);
            $h.handler($rating, 'mousemove', events.starMouseMove);
            $h.handler($rating, 'mouseleave', events.starMouseLeave);
            $h.handler($rating, 'keydown', events.keydown);
            $h.handler($rating, 'blur', events.blur);
            if (self.showClear && $clear.length) {
                $h.handler($clear, 'click touchstart', events.clearClick);
                $h.handler($clear, 'mousemove', events.clearMouseMove);
                $h.handler($clear, 'mouseleave', events.clearMouseLeave);
            }
            if ($form.length) {
                $h.handler($form, 'reset', events.resetForm, true);
            }
            $stars.off(mouseEvents).on(mouseEvents, function (e) {
                var $star = $(this), index = $star.index(), status = $star.parent().attr('class').slice(0, -1);
                self.$element.trigger('rating:' + e.type, [index + 1, status, $star]);
            });
            $h.handler(self.$container, 'click', events.focus);
            return $el;
        },
        _getStars: function (type) {
            var self = this, stars = '<span class="' + type + '-stars">', i;
            for (i = 1; i <= self.stars; i++) {
                stars += '<span class="star">' + self[type + 'Star'] + '</span>';
            }
            return stars + '</span>';
        },
        _initStarTitles: function (val) {
            var self = this;
            if (self.showCaptionAsTitle) {
                self._initCaptionTitle();
                return;
            }
            var starTitles = self.starTitles, setTitles;
            setTitles = function ($stars) {
                var i = 1, title;
                $stars.each(function () {
                    var $star = $(this), j, title;
                    if (typeof starTitles === 'function') {
                        j = i === Math.floor(val) ? val : i;
                        title = starTitles(j);
                    } else {
                        title = starTitles[i];
                    }
                    if (title) {
                        $star.attr({title: title});
                    }
                    i++;
                });
            };
            setTitles(self.$emptyStars.find('.star'));
            setTitles(self.$filledStars.find('.star'));
        },
        _setStars: function (pos) {
            var self = this, out = arguments.length ? self.calculate(pos) : self.calculate(), $el = self.$element,
                v = self._parseValue(out.val);
            $el.val(v);
            self.$filledStars.css('width', out.width);
            self._setCaption(out.caption);
            self.cache = out;
            self._initStarTitles(v);
            return $el;
        },
        showStars: function (val) {
            var self = this, v = self._parseValue(val);
            self.$element.val(v);
            return self._setStars();
        },
        calculate: function (pos) {
            var self = this, defaultVal = $h.isEmpty(self.$element.val()) ? 0 : self.$element.val(),
                val = arguments.length ? self.getValueFromPosition(pos) : defaultVal,
                caption = self.fetchCaption(val), width = self.getWidthFromValue(val);
            width += '%';
            return {caption: caption, width: width, val: val};
        },
        getValueFromPosition: function (pos) {
            var self = this, precision = $h.getDecimalPlaces(self.step), val, factor, maxWidth = self.$rating.width();
            factor = (self.diff * pos) / (maxWidth * self.step);
            factor = self.rtl ? Math.floor(factor) : Math.ceil(factor);
            val = $h.applyPrecision(parseFloat(self.min + factor * self.step), precision);
            val = Math.max(Math.min(val, self.max), self.minThreshold);
            return self.rtl ? (self.max - val) : val;
        },
        getWidthFromValue: function (val) {
            var self = this, min = self.min, max = self.max, factor, $r = self.$emptyStars, w;
            if (!val || val <= self.min || min === max) {
                return 0;
            }
            val = Math.max(val, self.minThreshold);
            w = $r.outerWidth();
            factor = w ? $r.width() / w : 1;
            if (val >= max) {
                return 100;
            }
            return (val - min) * factor * 100 / (max - min);
        },
        fetchCaption: function (rating) {
            var self = this, val = parseFloat(rating) || self.clearValue, css, cap, capVal, cssVal, caption,
                vCap = self.starCaptions, vCss = self.starCaptionClasses, width = self.getWidthFromValue(val);
            if (val && val !== self.clearValue) {
                val = $h.applyPrecision(val, $h.getDecimalPlaces(self.step));
            }
            cssVal = typeof vCss === 'function' ? vCss(val, width) : vCss[val];
            capVal = typeof vCap === 'function' ? vCap(val, width) : vCap[val];

            cap = $h.isEmpty(capVal) ? self.defaultCaption.replace(/\{rating}/g, val) : capVal;
            css = $h.isEmpty(cssVal) ? self.clearCaptionClass : cssVal;
            caption = (val === self.clearValue) ? self.clearCaption : cap;
            return '<span class="' + css + '">' + caption + '</span>';
        },
        destroy: function () {
            var self = this, $el = self.$element;
            if (!$h.isEmpty(self.$container)) {
                self.$container.before($el).remove();
            }
            $.removeData($el.get(0));
            return $el.off('rating').removeClass('rating rating-input');
        },
        create: function (options) {
            var self = this, opts = options || self.options || {};
            return self.destroy().rating(opts);
        },
        clear: function () {
            var self = this, title = '<span class="' + self.clearCaptionClass + '">' + self.clearCaption + '</span>';
            if (!self.inactive) {
                self._setCaption(title);
            }
            return self.showStars(self.clearValue).trigger('change').trigger('rating:clear');
        },
        reset: function () {
            var self = this;
            return self.showStars(self.initialValue).trigger('rating:reset');
        },
        update: function (val) {
            var self = this;
            return arguments.length ? self.showStars(val) : self.$element;
        },
        refresh: function (options) {
            var self = this, $el = self.$element;
            if (!options) {
                return $el;
            }
            return self.destroy().rating($.extend(true, self.options, options)).trigger('rating:refresh');
        }
    };

    $.fn.rating = function (option) {
        var args = Array.apply(null, arguments), retvals = [];
        args.shift();
        this.each(function () {
            var self = $(this), data = self.data('rating'), options = typeof option === 'object' && option,
                theme = options.theme || self.data('theme'), lang = options.language || self.data('language') || 'en',
                thm = {}, loc = {}, opts;
            if (!data) {
                if (theme) {
                    thm = $.fn.ratingThemes[theme] || {};
                }
                if (lang !== 'en' && !$h.isEmpty($.fn.ratingLocales[lang])) {
                    loc = $.fn.ratingLocales[lang];
                }
                opts = $.extend(true, {}, $.fn.rating.defaults, thm, $.fn.ratingLocales.en, loc, options, self.data());
                data = new Rating(this, opts);
                self.data('rating', data);
            }

            if (typeof option === 'string') {
                retvals.push(data[option].apply(data, args));
            }
        });
        switch (retvals.length) {
            case 0:
                return this;
            case 1:
                return retvals[0] === undefined ? this : retvals[0];
            default:
                return retvals;
        }
    };

    $.fn.rating.defaults = {
        theme: 'krajee-svg',
        language: 'en',
        stars: 5,
        tabindex: 0,
        keyboardEnabled: true,
        mouseEnabled: true,
        containerClass: '',
        size: 'md',
        animate: true,
        displayOnly: false,
        rtl: false,
        showClear: true,
        showCaption: true,
        starCaptionClasses: {
            0.5: 'caption-badge caption-danger',
            1: 'caption-badge caption-danger',
            1.5: 'caption-badge caption-warning',
            2: 'caption-badge caption-warning',
            2.5: 'caption-badge caption-info',
            3: 'caption-badge caption-info',
            3.5: 'caption-badge caption-primary',
            4: 'caption-badge caption-primary',
            4.5: 'caption-badge caption-success',
            5: 'caption-badge caption-success'
        },
        filledStar: '<span class="krajee-icon krajee-icon-star"></span>', // krajee-svg theme
        emptyStar: '<span class="krajee-icon krajee-icon-star"></span>',  // krajee-svg theme
        clearButton: '<span class="krajee-icon-clear"></span>',           // krajee-svg theme
        clearButtonBaseClass: 'clear-rating',
        clearButtonActiveClass: 'clear-rating-active',
        clearCaptionClass: 'caption-badge caption-secondary',
        clearValue: null,
        captionElement: null,
        clearElement: null,
        showCaptionAsTitle: false,
        hoverEnabled: true,
        hoverChangeCaption: true,
        hoverChangeStars: true,
        hoverOnClear: true,
        zeroAsNull: true
    };

    $.fn.ratingLocales.en = {
        defaultCaption: '{rating} Stars',
        starCaptions: {
            0.5: 'Half Star',
            1: 'Una Estrella',
            1.5: 'One & Half Star',
            2: 'Dos Estrellas',
            2.5: 'Two & Half Stars',
            3: 'Tres Estrellas',
            3.5: 'Three & Half Stars',
            4: 'Cuatro Estrellas',
            4.5: 'Four & Half Stars',
            5: 'Cinco Estrellas'
        },
        starTitles: {
            1: 'Una Estrella',
            2: 'Dos Estrellas',
            3: 'Tres Estrellas',
            4: 'Cuatro Estrellas',
            5: 'Cinco Estrellas'
        },
        clearButtonTitle: 'Clear',
        clearCaption: 'Sin Seleccionar'
    };

    $.fn.rating.Constructor = Rating;

    /**
     * Convert automatically inputs with class 'rating' into Krajee's star rating control.
     */
    $(document).ready(function () {
        var $input = $('input.rating');
        if ($input.length) {
            $input.removeClass('rating-loading').addClass('rating-loading').rating();
        }
    });
}));