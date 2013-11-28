(function ($) {

  // return object from path. When
  //    var a = {b: c{4}};
  // then
  //    fromPath(a, "b.c") === 4
  var fromPath = function(el, path) {
    var chunks = path.split('.');
    var i, chunk;
    for (i=0; i<chunks.length; i++) {
      chunk = chunks[i];
      el = el[chunk];
      if (!el) {
        break;
      }
    }
    return el;
  };


  // wrap function to make sure any other call will be dropped till `done`
  // callback is called
  var withLock = function (fn) {
    var locked = false;
    var wrapper = function () {
      if (locked) {
        return null;
      }
      locked = true;
      var done = function () {
        locked = false;
      };
      var args = Array.prototype.slice.call(arguments);
      args.unshift(done);
      return fn.apply(this, args);
    };
    wrapper.name = fn.name;
    return wrapper;
  };


  // wrap function to ensure it's context
  var wrapfn = function (ctx, fn) {
    var wrapper = function () {
      var args = Array.prototype.slice.call(arguments);
      return fn.apply(ctx, args);
    };
    wrapper.name = fn.name;
    return wrapper;
  };


  // selector is build upon three parameters:
  // 1) widget name that server can identyfy
  // 2) result handling method (append, html, text, prepend)
  // 3) selector for the destination. Selector is global, using sizzle
  //    selector, expecpt when it starts with '@' character. If so, searching
  //    is narrowed to the element that selector is parsed
  //
  // Only first parameter is required. Two others are defaulting to 'html' and
  // '@'
  function Widget($el, widgetSelector) {
    var chunks = widgetSelector.split(',');

    this.$el = $el;
    this.name = chunks[0];
    this._handler = chunks[1] || 'html';
    this._selector = chunks[2] || '@';
  }

  Widget.prototype = {
    selector: function () {
      if (this._selector === '@') {
        return this.$el;
      }
      if (this._selector[0] === '@') {
        return this.$el.find(this._selector.substring(1));
      }
      return $(this._selector);
    },
    handleData: function (data) {
      var selector = this.selector();
      if (selector.length === 0) {
        return;
      }
      var handler = selector[this._handler];
      if (handler === undefined) {
        throw new Error("Invalid handler '" + this._handler + "': " + this.name);
      }
      handler.call(selector, data);
    }
  };





  // for given list of widget names (wids), fetch content from the server and
  // load using given $el scope
  var loadWidgets = function (wids) {
    var chunks = [];
    var widgetByName = {};

    $.each(wids, function (_, wid) {
        var w = new Widget(wid.el, wid.attr);
        widgetByName[w.name] = w;
        chunks.push('wid=' + w.name);
    });

    var done = $.Deferred();

    $.getJSON(window.DYNAMIC_WIDGETS_URL + '?' + chunks.join('&'), function (resp) {
      $.each(resp, function (name, resp) {
        if (resp.error && console && console.warn) {
          if (console && console.warn) {
            console.warn("dynamic widget error:", resp.error);
          }
        }
        if (resp.html) {
          var w = widgetByName[name];
          if (w === undefined) {
            throw new Error("silly response: " + w.name, w);
          }
          w.handleData(resp.html);
        }
      });
      done.resolve();
    });

    return done;
  };



  var loadDynamicWidgets = function ($el) {
    $el.on('mouseenter', '[dw-hover]', withLock(function (done) {
      var $el = $(this);
      var wid = $el.attr('dw-hover');
      loadWidgets([{el: $el, attr: wid}]).done(function () {
        if ($el.attr('dw-once') !== undefined) {
          $el.removeAttr('dw-hover').removeAttr('dw-once');
        }
      }).always(done);
    }));

    $el.on('click', '[dw-click]', withLock(function (done) {
      var $el = $(this);
      var wid = $el.attr('dw-click');
      loadWidgets([{el: $el, attr: wid}]).done(function () {
        if ($el.attr('dw-once') !== undefined) {
          $el.removeAttr('dw-click').removeAttr('dw-once');
        }
      }).always(done);
    }));

    // for given $el selector, find all [dw-load] elements and load content
    // for them, according to name set with this attribute
    var wids = [];
    $el.find('[dw-load]').each(function () {
      wids.push({el: $(this), attr: $(this).attr('dw-load')});
    });
    loadWidgets(wids);
  };



  $(function () {
    if (!window.DYNAMIC_WIDGETS_URL) {
      if (console && console.warn) {
        console.warn("DYNAMIC_WIDGETS_URL missing");
      }
      return;
    }
    loadDynamicWidgets($(document));
  });

}(jQuery));
