/**
 * This file is used to embed an iFrame into Gmail to show content on other
 * sites that the user has requested.
 *
 * This is for working around the Chrome/WebKit bug listed here:
 * https://code.google.com/p/chromium/issues/detail?id=408932
 */

var messageId;
var parentOrigin;

var iframe;

window.addEventListener('message', function(event){
	if(event.data.id && event.data.eventName === 'init' && event.origin.match(/^https:\/\/\w+\.google\.com$/)){
		messageId = event.data.id;
		parentOrigin = event.origin;

		setupIFrame(event.data.iframeSrc);

		return;
	}

	if(event.origin.match(/^https:\/\/\w+\.google\.com$/)){
		iframe.contentWindow.postMessage(event.data, '*');
		return;
	}

	var newData = {
		data: event.data,
		senderId: messageId
	};
	window.parent.postMessage(newData, parentOrigin);
});

function setupIFrame(src){
	iframe = document.createElement('iframe');
	iframe.src = src;
	iframe.setAttribute('style', 'height: 100%; width: 100%; border: 0');
	document.body.appendChild(iframe);
}
