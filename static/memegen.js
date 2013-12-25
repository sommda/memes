var memeImage = new Image();

$(document).ready(function() {
	$("button#go").click(function() {
		var imageHash = $("#image-hash").val();
		img = new Image();
		img.src = "/api/v1.0/images/" + imageHash + "/render";

		$(img).load(function() {
			memeImage = img;
			drawCanvas();
		});
	});

	$("button#get-images").click(function() {
		$.ajax({
		    url: '/api/v1.0/images',
		    dataType: 'json',
		    success: gotImages
		});
	});
});

function gotImages(data) {
    $.each(data.images, function(i, image) {
	$("<img>")
	    .attr({class: "img-thumbnail", src: image.url, width: 128, id: image.hash})
	    .appendTo("#image-holder")
	    .click(function() {
		    $("#image-hash").val(this.id);
		});
    });
}

function drawCanvas() {
    var memeCanvas = $("canvas#meme")[0];
    var memeContext = memeCanvas.getContext("2d");
    desiredHeight = 512;
    ratio = desiredHeight / memeImage.height;
    desiredWidth = memeImage.width * ratio;
    memeCanvas.width = desiredWidth;
    memeCanvas.height = desiredHeight;

    memeContext.drawImage(memeImage, 0, 0, desiredWidth, desiredHeight);

    textSize = desiredHeight / 12;
    margin = desiredHeight / 16;
    memeContext.font= "" + textSize + "px Impact";
    memeContext.fillStyle="#FFFFFF";
    memeContext.strokeStyle="#000000";
    memeContext.lineWidth = 4;

    var topText = $("#top-text").val();
    var topTextMeasure = memeContext.measureText(topText);
    var topX = (memeCanvas.width - topTextMeasure.width) / 2;
    var topY = textSize + margin;
    memeContext.strokeText(topText, topX, topY);
    memeContext.fillText(topText, topX, topY);

    var botText = $("#bottom-text").val();
    var botTextMeasure = memeContext.measureText(botText);
    var botX = (memeCanvas.width - botTextMeasure.width) / 2;
    var botY = memeCanvas.height - margin;
    memeContext.strokeText(botText, botX, botY);
    memeContext.fillText(botText, botX, botY);
}
