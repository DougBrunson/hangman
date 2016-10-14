"use strict";function copyToClipboard(a){var b=document.createElement("div");b.contentEditable=!0,document.body.appendChild(b),b.innerHTML=a,b.unselectable="off",b.focus(),document.execCommand("SelectAll"),document.execCommand("Copy",!1,null),document.body.removeChild(b)}function selectTab(a){chrome.tabs.getAllInWindow(null,function(b){b.length<=1||chrome.tabs.getSelected(null,function(c){var d;switch(a){case"next":d=b[(c.index+1+b.length)%b.length];break;case"previous":d=b[(c.index-1+b.length)%b.length];break;case"first":d=b[0];break;case"last":d=b[b.length-1]}chrome.tabs.update(d.id,{selected:!0})})})}chrome.runtime.onMessage.addListener(function(a,b,c){var d=a.action;if("getKeys"===d)c(localStorage.shortkeys);else if("cleardownloads"===d)chrome.browsingData.remove({since:0},{downloads:!0});else if("nexttab"===d)selectTab("next");else if("prevtab"===d)selectTab("previous");else if("firsttab"===d)selectTab("first");else if("lasttab"===d)selectTab("last");else if("newtab"===d)chrome.tabs.create({});else if("closetab"===d)chrome.tabs.getSelected(null,function(a){chrome.tabs.remove(a.id)});else if("clonetab"===d)chrome.tabs.getSelected(null,function(a){chrome.tabs.duplicate(a.id)});else if("onlytab"===d)chrome.tabs.query({windowId:chrome.windows.WINDOW_ID_CURRENT,pinned:!1,active:!1},function(a){var b=[];a.forEach(function(a){b.push(a.id)}),chrome.tabs.remove(b)});else if("togglepin"===d)chrome.tabs.getSelected(null,function(a){var b=!a.pinned;chrome.tabs.update(a.id,{pinned:b})});else if("copyurl"===d)copyToClipboard(a.text);else if("movetableft"===d)b.tab.index>0&&chrome.tabs.move(b.tab.id,{index:b.tab.index-1});else if("movetabright"===d)chrome.tabs.move(b.tab.id,{index:b.tab.index+1});else if("gototab"===d){var e=function(){chrome.tabs.create({url:a.openurl})};a.matchurl?chrome.tabs.query({url:a.matchurl,currentWindow:!0},function(a){a.length>0?chrome.tabs.update(a[0].id,{selected:!0}):e()}):e()}else"openbookmark"===d?chrome.bookmarks.search({title:a.bookmark},function(c){for(var d,e=c.length;e-->0;){var f=c[e];if(f.url&&f.title===a.bookmark){d=f;break}}chrome.tabs.update(b.tab.id,{url:decodeURI(d.url)})}):c({})});