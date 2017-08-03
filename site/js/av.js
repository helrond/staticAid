window.onload = function() {

	// asset
	var asset = document.getElementById("asset");

	if(asset) {

		// Asset data
		var assetType = asset.getAttribute('data-type');
		var assetTitle = document.getElementById('asset-title');
		var assetSource = asset.children[0].getAttribute('src');
		var assetType = assetSource.split('.').pop().toUpperCase();
		// get and assign asset size and file type to HTML elements
		var getAssetSize = $.ajax({
			  type: "HEAD",
			  url: assetSource,
			  success: function(msg){
			    var assetByteSize = getAssetSize.getResponseHeader('Content-Length');
					var assetSize = getReadableFileSizeString(assetByteSize);
					document.getElementById('download-details').innerHTML = assetType + '/' + assetSize;
			  }
			});

		// Convert bytes to human readable string
		function getReadableFileSizeString(fileSizeInBytes) {
				var i = -1;
				var byteUnits = [' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
				do {
						fileSizeInBytes = fileSizeInBytes / 1024;
						i++;
				} while (fileSizeInBytes > 1024);
				return Math.max(fileSizeInBytes, 0.1).toFixed(1) + byteUnits[i];
		};

		// Buttons
		var playButton = document.getElementById("play-pause");
		var muteButton = document.getElementById("mute");
		var fullScreenButton = document.getElementById("full-screen");
		var downloadButton = document.getElementById("download");
		var timeButton = document.getElementById("time");

		// Sliders
		var seekBar = document.getElementById("seek-bar");
		var volumeBar = document.getElementById("volume-bar");

		function padLeft(string,pad,length) {
    	return (new Array(length+1).join(pad)+string).slice(-length);
		}

		function setKeyFrames (duration) {
			var quarter = (duration / 4).toFixed(1)
			sessionStorage.setItem('one', quarter)
			sessionStorage.setItem('two', (quarter * 2).toFixed(1))
			sessionStorage.setItem('three', (quarter * 3).toFixed(1))
		}

		function assetTimeUpdate () {
				var curTime = asset.currentTime.toFixed(1)
				switch (curTime) {
					case sessionStorage.getItem('one'):
						ga('send', 'event', assetType, '25% played', assetTitle)
						sessionStorage.setItem('one', null)
					case sessionStorage.getItem('two'):
						ga('send', 'event', assetType, '50% played', assetTitle)
						sessionStorage.setItem('two', null)
					case sessionStorage.getItem('three'):
						ga('send', 'event', assetType, '75% played', assetTitle)
						sessionStorage.setItem('three', null)
				}
		}

		asset.addEventListener("canplay", function (event) {
		  asset.classList.remove("background");
		});

		// Event listener for the play/pause button
		playButton.addEventListener("click", function() {
			if (asset.paused == true) {
				asset.play();
				playButton.innerHTML = '<span class="glyphicon glyphicon-pause" aria-hidden="true"></span>';
				ga('send', 'event', assetType, 'play', assetTitle);
				setKeyFrames(this.duration)
			} else {
				asset.pause();
				playButton.innerHTML = '<span class="glyphicon glyphicon-play" aria-hidden="true"></span>';
				ga('send', 'event', assetType, 'pause', assetTitle);
			}
		});

		// Event listener for the mute button
		muteButton.addEventListener("click", function() {
			if (asset.muted == false) {
				asset.muted = true;
				muteButton.innerHTML = '<span class="glyphicon glyphicon-volume-off" aria-hidden="true"></span>';
				volumeBar.value = 0;
				ga('send', 'event', assetType, 'mute', assetTitle)
			} else {
				asset.muted = false;
				muteButton.innerHTML = '<span class="glyphicon glyphicon-volume-up" aria-hidden="true"></span>';
				volumeBar.value = asset.value;
				ga('send', 'event', assetType, 'unmute', assetTitle)
			}
		});

		// Event listener for the seek bar
		seekBar.addEventListener("change", function() {
			var time = asset.duration * (seekBar.value / 100);
			asset.currentTime = time;
		});

		// Update the seek bar as the asset plays
		asset.addEventListener("timeupdate", function() {
			var value = (100 / asset.duration) * asset.currentTime;
			seekBar.value = value;
			timeButton.innerHTML = new Date(asset.currentTime * 1000).toISOString().substr(11, 8);;
			assetTimeUpdate();
		});

		// Pause the asset when the seek handle is being dragged
		seekBar.addEventListener("mousedown", function() {
			playButton.innerHTML = '<span class="glyphicon glyphicon-pause" aria-hidden="true"></span>';
			asset.pause();
		});

		// Play the asset when the seek handle is dropped
		seekBar.addEventListener("mouseup", function() {
			playButton.innerHTML = '<span class="glyphicon glyphicon-pause" aria-hidden="true"></span>';
			asset.play();
		});

		// Event listener for the volume bar
		volumeBar.addEventListener("change", function() {
			asset.volume = volumeBar.value;
			ga('send', 'event', assetType, 'volume change', assetTitle);
		});

		// Event listener for the full-screen button
		if(fullScreenButton) {
				fullScreenButton.addEventListener("click", function() {
				if (asset.requestFullscreen) {
					asset.requestFullscreen();
				} else if (asset.mozRequestFullScreen) {
					asset.mozRequestFullScreen(); // Firefox
				} else if (asset.webkitRequestFullscreen) {
					asset.webkitRequestFullscreen(); // Chrome and Safari
				}
				ga('send', 'event', assetType, 'full screen', assetTitle);
			});
		}

		downloadButton.addEventListener("mousedown", function() {
			ga('send', 'event', assetType, 'download', assetTitle);
		});

		asset.addEventListener('ended', function() {
			ga('send', 'event', assetType, 'ended', assetTitle);
		});
	}
}
