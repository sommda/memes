var memeImage = new Image();

$(document).ready(function() {
    $("#create-interface").hide();
    $("#view-interface").show();

    $("#show-create").click(function() {
	$("#show-create").addClass("active");
	$("#show-view").removeClass("active");
	$("#view-interface").hide();
	$("#create-interface").show();
    });

    $("#show-view").click(function() {
	$("#show-view").addClass("active");
	$("#show-create").removeClass("active");
	$("#create-interface").hide();
	$("#view-interface").show();
    });

    $("button#get-images").click(getImages);

    $("button#create-meme").click(function() {
	var data = {
	    'image-hash': $("#image-hash").val(),
	    'top-text': $("#top-text").val(),
	    'bottom-text': $("#bottom-text").val()
	}
	$.ajax({
	    type: "POST",
            url: '/api/v1.0/memes',
	    data: data,
	    dataType: 'json',
	    success: function(result) {
		alert("success: " + result);
	    }
	});
    });

    $("button#upload-image").click(function() {
	var formData = new FormData($("#upload-image-form")[0]);
	$.ajax({
	    url: 'api/v1.0/images',
	    type: 'POST',
	    success: function() {
		getImages();
		alert("Image upload successful!");
	    },
	    error: function() {
		alert("Image upload failed!");
	    },
	    data: formData,
	    cache: false,
	    contentType: false,
	    processData: false
	});
    });

    $("input#top-text").change(function() {
	drawCanvas();
    });

    $("input#bottom-text").change(function() {
	drawCanvas();
    });

    // Load memes into the view pane
    $("#temp-image-holder").hide();
    $.ajax({
	type: "GET",
	url: '/api/v1.0/memes',
	dataType: 'json',
	success: function(data) {
	    $.each(data.memes, function(i, meme) {
		var div = $("<div>")
		    .attr({id: meme["image-hash"], class: "col-md-1 thumbnail"})
		    .appendTo("#meme-holder");
		$("<img>").attr({
		    src: "/api/v1.0/images/" + meme["image-hash"] + "/render"}).hide()
		    .appendTo("#temp-image-holder").load(function() {
			var desiredHeight = 256;
			var desiredWidth = this.width * (desiredHeight / this.height);
			var canvas = $("<canvas>")
			    .attr({width: desiredWidth, height: desiredHeight}).appendTo(div);
			var context = canvas[0].getContext("2d");
			drawMeme(canvas[0], this, meme["top-text"], meme["bottom-text"]); 
			this.remove();
			div.width(desiredWidth);
			div.height(desiredHeight);
		    });
	    });
	}
    });
});

function getImages() {
    $.ajax({
	url: '/api/v1.0/images',
	dataType: 'json',
	success: gotImages
    });
}

function gotImages(data) {
    $("#image-holder").empty();
    $.each(data.images, function(i, image) {
	$("<img>")
	    .hide()
	    .attr({class: "img-thumbnail", src: image.url, id: image.hash})
	    .appendTo("#image-holder")
	    .load(function() {
		var desiredHeight = 128;
		var desiredWidth = this.width * (desiredHeight / this.height);
		this.height = desiredHeight;
		this.width = desiredWidth;
		$(this).show();
	    })
	    .click(function() {
		$("#image-hash").val(this.id);
		memeImage = this;
		drawCanvas();
	    });
    });
}

function drawMeme(canvas, memeImage, topText, bottomText) {
    var context = canvas.getContext("2d");
    context.drawImage(memeImage, 0, 0, canvas.width, canvas.height);

    textSize = canvas.height / 12;
    margin = canvas.height / 16;
    context.font= "" + textSize + "px Impact";
    context.fillStyle="#FFFFFF";
    context.strokeStyle="#000000";
    context.lineWidth = canvas.height / 64;
    if (context.lineWidth < 3)
	context.lineWidth = 3;

    var topTextMeasure = context.measureText(topText);
    var topX = (canvas.width - topTextMeasure.width) / 2;
    var topY = textSize + margin;
    context.strokeText(topText, topX, topY);
    context.fillText(topText, topX, topY);

    var bottomTextMeasure = context.measureText(bottomText);
    var bottomX = (canvas.width - bottomTextMeasure.width) / 2;
    var bottomY = canvas.height - margin;
    context.strokeText(bottomText, bottomX, bottomY);
    context.fillText(bottomText, bottomX, bottomY);
}

function drawCanvas() {
    var memeCanvas = $("canvas#meme")[0];
    var topText = $("#top-text").val();
    var bottomText = $("#bottom-text").val();
    desiredHeight = 512;
    ratio = desiredHeight / memeImage.height;
    desiredWidth = memeImage.width * ratio;
    memeCanvas.width = desiredWidth;
    memeCanvas.height = desiredHeight;
    drawMeme(memeCanvas, memeImage, topText, bottomText);
}
