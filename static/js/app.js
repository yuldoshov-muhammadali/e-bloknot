/*
  app.js — "Bugun"/kun sahifasi va "Sozlamalar" sahifasidagi interaktiv qismlar.
  Vanilla JavaScript (React yo'q). Sahifa qayta yuklanmaydi.

  Asosiy qismlar:
    - showToast()           : pastda qisqa xabar
    - picker (panel)        : guruh tanlash
    - refreshDay()          : kun mazmunini /fragment orqali qayta chizish
    - belgilash             : Bajarildi / Bajarolmadim / Bekor qilish
    - taymer                : ▶/⏸ (localStorage da saqlanadi, bitta ishlaydi)
    - ko'chirish            : kechikkanlarni bugunga / ertaga
    - Sozlamalar            : o'rgatilgan so'zlar
*/

(function () {
  "use strict";

  var CATEGORIES = window.CATEGORIES || [];
  var catById = {};
  CATEGORIES.forEach(function (c) {
    catById[c.id] = c;
  });

  // ---------------------------------------------------------
  //   Toast
  // ---------------------------------------------------------
  function showToast(msg, type) {
    var cont = document.getElementById("toast-container");
    if (!cont) return;
    var el = document.createElement("div");
    el.className = "toast toast-" + (type || "success");
    el.textContent = msg;
    cont.appendChild(el);
    requestAnimationFrame(function () {
      el.classList.add("show");
    });
    setTimeout(function () {
      el.classList.remove("show");
      setTimeout(function () {
        el.remove();
      }, 300);
    }, 3000);
  }

  // ---------------------------------------------------------
  //   Serverga JSON yuborish
  // ---------------------------------------------------------
  // Sahifadagi CSRF tokenini o'qiymiz (base.html dagi <meta>).
  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(), // CSRF himoyasi uchun
      },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!res.ok || !data.ok) {
            throw { status: res.status, data: data };
          }
          return data;
        });
    });
  }

  function errMsg(err) {
    if (err && err.status === 404) return "Topilmadi (bu sizning yozuvingiz emas).";
    if (err && err.data && err.data.error) return err.data.error;
    return "Xatolik yuz berdi.";
  }

  // ---------------------------------------------------------
  //   Guruh tanlash paneli (picker / bottom sheet)
  // ---------------------------------------------------------
  var pickerCb = null;

  function buildPicker() {
    var overlay = document.getElementById("picker-overlay");
    if (overlay) return overlay;

    overlay = document.createElement("div");
    overlay.id = "picker-overlay";
    overlay.className = "picker-overlay";
    overlay.hidden = true;

    var sheet = document.createElement("div");
    sheet.className = "picker-sheet";

    var title = document.createElement("div");
    title.className = "picker-title";
    title.textContent = "Guruhni tanlang";
    sheet.appendChild(title);

    var list = document.createElement("div");
    list.className = "picker-list";
    CATEGORIES.forEach(function (c) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "picker-option";
      b.dataset.id = c.id;
      b.textContent = c.emoji + "  " + c.name;
      b.addEventListener("click", function () {
        var cb = pickerCb;
        closePicker();
        if (cb) cb(c.id);
      });
      list.appendChild(b);
    });
    sheet.appendChild(list);
    overlay.appendChild(sheet);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closePicker();
    });

    document.body.appendChild(overlay);
    return overlay;
  }

  function openPicker(currentId, cb) {
    var overlay = buildPicker();
    pickerCb = cb;
    overlay.querySelectorAll(".picker-option").forEach(function (o) {
      o.classList.toggle("selected", o.dataset.id === currentId);
    });
    overlay.hidden = false;
    document.body.classList.add("no-scroll");
  }

  function closePicker() {
    var overlay = document.getElementById("picker-overlay");
    if (overlay) overlay.hidden = true;
    pickerCb = null;
    document.body.classList.remove("no-scroll");
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closePicker();
  });

  // ---------------------------------------------------------
  //   Kun mazmunini qayta chizish
  // ---------------------------------------------------------
  var dayContent = document.getElementById("day-content");

  function currentDate() {
    return dayContent ? dayContent.dataset.date : "";
  }

  function refreshDay() {
    if (!dayContent) return Promise.resolve();
    return fetch("/fragment?date=" + encodeURIComponent(currentDate()))
      .then(function (res) {
        return res.text();
      })
      .then(function (html) {
        dayContent.innerHTML = html;
        initTimers();
      })
      .catch(function () {});
  }

  function closeMenus() {
    document.querySelectorAll(".menu-dropdown").forEach(function (d) {
      d.hidden = true;
    });
  }

  // ---------------------------------------------------------
  //   TAYMER (localStorage da saqlanadi — bitta ishlaydi)
  // ---------------------------------------------------------
  var TIMER_KEY = "ebTimer";
  var tickHandle = null;

  function getTimer() {
    try {
      return JSON.parse(localStorage.getItem(TIMER_KEY));
    } catch (e) {
      return null;
    }
  }
  function setTimer(obj) {
    localStorage.setItem(TIMER_KEY, JSON.stringify(obj));
  }
  function clearTimer() {
    localStorage.removeItem(TIMER_KEY);
  }

  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }
  function fmt(sec) {
    return pad(Math.floor(sec / 60)) + ":" + pad(sec % 60);
  }

  function renderTick() {
    var t = getTimer();
    if (!t) return;
    var card = document.querySelector('.task-item[data-id="' + t.id + '"]');
    if (!card) return;
    var sec = Math.floor((Date.now() - t.start) / 1000);
    var live = card.querySelector(".timer-live");
    if (live) {
      live.hidden = false;
      live.textContent = fmt(sec);
    }
  }

  // Har safar kun qayta chizilgandan keyin chaqiriladi.
  function initTimers() {
    if (tickHandle) {
      clearInterval(tickHandle);
      tickHandle = null;
    }
    document.querySelectorAll(".timer-btn").forEach(function (b) {
      b.textContent = "▶";
    });
    document.querySelectorAll(".timer-live").forEach(function (l) {
      l.hidden = true;
    });

    var t = getTimer();
    if (t) {
      var card = document.querySelector('.task-item[data-id="' + t.id + '"]');
      if (card) {
        var btn = card.querySelector(".timer-btn");
        if (btn) btn.textContent = "⏸";
      }
      renderTick();
      tickHandle = setInterval(renderTick, 1000);
    }
  }

  // Ishlayotgan taymerni to'xtatib, o'tgan vaqtni (daqiqa) vazifaga qo'shadi.
  function commitTimer() {
    var t = getTimer();
    if (!t) return Promise.resolve(false);
    var sec = Math.floor((Date.now() - t.start) / 1000);
    var mins = Math.max(1, Math.round(sec / 60)); // kamida 1 daqiqa
    clearTimer();
    return postJSON("/api/task/" + t.id + "/minutes", { mode: "add", value: mins })
      .then(function () {
        return true;
      })
      .catch(function () {
        return false;
      });
  }

  function startTimer(id) {
    var t = getTimer();
    var chain = t ? commitTimer() : Promise.resolve(); // oldingisini saqlab to'xtatamiz
    chain.then(function () {
      setTimer({ id: id, start: Date.now() });
      refreshDay();
    });
  }

  function pauseTimer() {
    commitTimer().then(function () {
      refreshDay();
    });
  }

  // ---------------------------------------------------------
  //   Joyida tahrirlash (vazifa matni)
  // ---------------------------------------------------------
  function startEdit(li) {
    var titleSpan = li.querySelector(".task-title");
    var oldText = titleSpan.textContent;
    var input = document.createElement("input");
    input.type = "text";
    input.className = "edit-input";
    input.value = oldText;
    titleSpan.replaceWith(input);
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);

    var done = false;
    function finish() {
      if (done) return;
      done = true;
      var val = input.value.trim();
      if (val.length < 2 || val === oldText) {
        refreshDay();
        return;
      }
      postJSON("/api/task/" + li.dataset.id + "/edit", { title: val })
        .then(function () {
          showToast("Saqlandi");
          refreshDay();
        })
        .catch(function (err) {
          showToast(errMsg(err), "error");
          refreshDay();
        });
    }
    function cancel() {
      if (done) return;
      done = true;
      refreshDay();
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        finish();
      } else if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      }
    });
    input.addEventListener("blur", finish);
  }

  // Vaqtni qo'lda kiritish (⏱ ... daq ni bosganda).
  function startMinutesEdit(li) {
    var box = li.querySelector(".time-box");
    var disp = li.querySelector(".minutes-display");
    if (!disp) return;
    var input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = "1440";
    input.className = "minutes-input";
    input.value = li.dataset.minutes || "0";
    box.insertBefore(input, disp);
    disp.hidden = true;
    input.focus();
    input.select();

    var done = false;
    function finish() {
      if (done) return;
      done = true;
      var val = parseInt(input.value, 10);
      if (isNaN(val) || val < 0 || val > 1440) {
        showToast("Vaqt 0–1440 daqiqa oralig'ida bo'lsin", "error");
        refreshDay();
        return;
      }
      postJSON("/api/task/" + li.dataset.id + "/minutes", { mode: "set", value: val })
        .then(function () {
          refreshDay();
        })
        .catch(function (err) {
          showToast(errMsg(err), "error");
          refreshDay();
        });
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        finish();
      } else if (e.key === "Escape") {
        e.preventDefault();
        done = true;
        refreshDay();
      }
    });
    input.addEventListener("blur", finish);
  }

  // ---------------------------------------------------------
  //   Kun sahifasidagi hamma bosishlar (event delegation)
  // ---------------------------------------------------------
  if (dayContent) {
    dayContent.addEventListener("click", function (e) {
      var li = e.target.closest(".task-item");

      // --- Vazifa kartochkasidagi amallar ---
      if (li) {
        // Guruh chipi — panelni ochish.
        if (e.target.closest(".chip")) {
          var cid = li.dataset.id;
          openPicker(li.dataset.category, function (newCat) {
            postJSON("/api/task/" + cid + "/category", { category: newCat })
              .then(function () {
                showToast("Guruh o'zgartirildi. Eslab qoldim ✓");
                refreshDay();
              })
              .catch(function (err) {
                showToast(errMsg(err), "error");
              });
          });
          return;
        }
        // "⋯" menyu.
        if (e.target.closest(".menu-btn")) {
          var dd = li.querySelector(".menu-dropdown");
          var wasHidden = dd.hidden;
          closeMenus();
          dd.hidden = !wasHidden;
          return;
        }
        if (e.target.closest(".edit-btn")) {
          closeMenus();
          startEdit(li);
          return;
        }
        if (e.target.closest(".move-tomorrow-btn")) {
          closeMenus();
          var md = e.target.closest(".move-tomorrow-btn").dataset.date;
          postJSON("/api/task/" + li.dataset.id + "/move", { date: md })
            .then(function () {
              showToast("Ertaga ko'chirildi");
              refreshDay();
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
          return;
        }
        if (e.target.closest(".delete-btn")) {
          closeMenus();
          if (confirm("Vazifani o'chirasizmi?")) {
            postJSON("/api/task/" + li.dataset.id + "/delete", {})
              .then(function () {
                showToast("Vazifa o'chirildi");
                refreshDay();
              })
              .catch(function (err) {
                showToast(errMsg(err), "error");
              });
          }
          return;
        }

        // Bajarildi (agar taymer ishlayotgan bo'lsa, avval saqlaymiz).
        if (e.target.closest(".done-btn")) {
          var did = li.dataset.id;
          var tm = getTimer();
          var pre =
            tm && String(tm.id) === String(did) ? commitTimer() : Promise.resolve();
          pre
            .then(function () {
              return postJSON("/api/task/" + did + "/status", { status: "done" });
            })
            .then(function () {
              showToast("Bajarildi ✅");
              refreshDay();
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
          return;
        }
        // Bajarolmadim — sabab maydonini ochamiz.
        if (e.target.closest(".fail-btn")) {
          var box = li.querySelector(".reason-box");
          if (box) {
            box.hidden = false;
            var inp = box.querySelector(".reason-input");
            if (inp) inp.focus();
          }
          return;
        }
        // Tez tanlov tugmasi — sababni inputga yozadi.
        if (e.target.closest(".reason-pick")) {
          var rb = li.querySelector(".reason-box");
          rb.querySelector(".reason-input").value = e.target.textContent.trim();
          return;
        }
        // Sababni saqlash.
        if (e.target.closest(".reason-save")) {
          var reason = li.querySelector(".reason-input").value.trim();
          postJSON("/api/task/" + li.dataset.id + "/status", {
            status: "failed",
            reason: reason,
          })
            .then(function () {
              showToast("Belgilandi");
              refreshDay();
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
          return;
        }
        // Bekor qilish — yana todo.
        if (e.target.closest(".undo-btn")) {
          postJSON("/api/task/" + li.dataset.id + "/status", { status: "todo" })
            .then(function () {
              showToast("Bekor qilindi");
              refreshDay();
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
          return;
        }
        // Taymer ▶/⏸.
        if (e.target.closest(".timer-btn")) {
          var tid = li.dataset.id;
          var cur = getTimer();
          if (cur && String(cur.id) === String(tid)) {
            pauseTimer();
          } else {
            startTimer(tid);
          }
          return;
        }
        // Vaqtni qo'lda kiritish.
        if (e.target.closest(".minutes-display")) {
          startMinutesEdit(li);
          return;
        }
        return;
      }

      // --- Kechikkanlar bloki ---
      var ov = e.target.closest(".overdue-item");
      if (ov && e.target.closest(".move-today-btn")) {
        var td = e.target.closest(".move-today-btn").dataset.date;
        postJSON("/api/task/" + ov.dataset.id + "/move", { date: td })
          .then(function () {
            showToast("Bugunga ko'chirildi");
            refreshDay();
          })
          .catch(function (err) {
            showToast(errMsg(err), "error");
          });
        return;
      }
      if (ov && e.target.closest(".drop-btn")) {
        postJSON("/api/task/" + ov.dataset.id + "/drop", {})
          .then(function () {
            showToast("Voz kechildi");
            refreshDay();
          })
          .catch(function (err) {
            showToast(errMsg(err), "error");
          });
        return;
      }
      // Hammasini bugunga ko'chirish.
      if (e.target.closest(".move-all-btn")) {
        var d = e.target.closest(".move-all-btn").dataset.date;
        var ids = Array.prototype.map.call(
          document.querySelectorAll(".overdue-item"),
          function (x) {
            return x.dataset.id;
          }
        );
        moveAll(ids, d);
        return;
      }
    });
  }

  // Kechikkanlarni ketma-ket ko'chiradi.
  function moveAll(ids, dateStr) {
    var chain = Promise.resolve();
    ids.forEach(function (id) {
      chain = chain.then(function () {
        return postJSON("/api/task/" + id + "/move", { date: dateStr }).catch(
          function () {}
        );
      });
    });
    chain.then(function () {
      showToast(ids.length + " ta vazifa bugunga ko'chirildi");
      refreshDay();
    });
  }

  // ---------------------------------------------------------
  //   "Sozlamalar" sahifasi — o'rgatilgan so'zlar
  // ---------------------------------------------------------
  var keywords = document.getElementById("keywords");
  if (keywords) {
    keywords.addEventListener("click", function (e) {
      var li = e.target.closest(".keyword-item");
      if (!li) return;
      if (e.target.closest(".chip")) {
        var id = li.dataset.id;
        openPicker(li.dataset.category, function (newCat) {
          postJSON("/api/keyword/" + id + "/category", { category: newCat })
            .then(function () {
              var c = catById[newCat];
              li.dataset.category = newCat;
              li.querySelector(".chip").textContent = c.emoji + " " + c.name;
              showToast("Guruh o'zgartirildi ✓");
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
        });
        return;
      }
      if (e.target.closest(".kw-delete-btn")) {
        if (confirm("Bu so'zni o'chirasizmi?")) {
          postJSON("/api/keyword/" + li.dataset.id + "/delete", {})
            .then(function () {
              li.remove();
              showToast("O'chirildi");
              if (!keywords.querySelector(".keyword-item")) {
                var empty = document.createElement("div");
                empty.className = "card placeholder empty-state";
                empty.innerHTML =
                  '<p class="empty-emoji">🧠</p><p>Hali hech narsa o\'rganilmagan. Vazifa guruhini o\'zgartirsangiz, platforma eslab qoladi.</p>';
                keywords.innerHTML = "";
                keywords.appendChild(empty);
              }
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
        }
        return;
      }
    });
  }

  // ---------------------------------------------------------
  //   Hisobot sahifasi — "uzoq kutayotganlar" ko'chirish/voz kechish
  // ---------------------------------------------------------
  var report = document.getElementById("report");
  if (report) {
    report.addEventListener("click", function (e) {
      var li = e.target.closest(".pending-item");
      if (!li) return;
      var id = li.dataset.id;

      if (e.target.closest(".report-move-btn")) {
        var d = e.target.closest(".report-move-btn").dataset.date;
        postJSON("/api/task/" + id + "/move", { date: d })
          .then(function () {
            showToast("Bugunga ko'chirildi");
            location.reload(); // hisobotni yangilaymiz
          })
          .catch(function (err) {
            showToast(errMsg(err), "error");
          });
        return;
      }
      if (e.target.closest(".report-drop-btn")) {
        if (confirm("Bu vazifadan voz kechasizmi?")) {
          postJSON("/api/task/" + id + "/drop", {})
            .then(function () {
              showToast("Voz kechildi");
              location.reload();
            })
            .catch(function (err) {
              showToast(errMsg(err), "error");
            });
        }
        return;
      }
    });
  }

  // Boshqa joyga bosilsa menyularni yopamiz.
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".task-actions")) closeMenus();
  });

  // Sahifa ochilganda taymer holatini tiklaymiz.
  initTimers();
})();
