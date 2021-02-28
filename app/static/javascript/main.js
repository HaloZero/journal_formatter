$(function() {
	setupAnalyze()
	setupClassify()
	setupAnalysisProgress()
});

/// setup the button to analyze a journal entry
function setupAnalyze() {
	$('button.analyze_sentiment').on('click', function() {
		var $entryElement = $(this).closest(".entry").find("pre")
		var entryText = $entryElement.text()
		$.getJSON(
			'/analyze_sentiment', 
			{'entry_text': entryText, 'use_internal_classifier': 0 },
			function (response) {
				$.each(response, function(key, value) {
			        if (value <= -0.1) {
			        	entryText = entryText.replace(key, "<span class=negative_2>" + key + "</span>")
			        } else if (value < 0) {
			        	entryText = entryText.replace(key, "<span class=negative_1>" + key + "</span>")
			        } else if (value == 0) {
			        	entryText = entryText.replace(key, "<span class=neutral>" + key + "</span>")
			        } else if (value < 0.1) {
			        	entryText = entryText.replace(key, "<span class=positive_1>" + key + "</span>")
			        } else {
						entryText = entryText.replace(key, "<span class=positive_2>" + key + "</span>")
			        }
			    });
			    $entryElement.html(entryText)
			})
	});
}

function setupClassify() {
	$(".sentence button").on('click', function() {
		var sentence = $(this).closest(".sentence").find("pre").text()
		var sentiment = $(this).data('sentiment')
		var $sentence = $(this).closest(".sentence")
		if ($sentence.hasClass('disabled')) {
			return 
		}

		$.post(
			'post_classify_sentence',
			{ 'sentence' : sentence, 'sentiment' : sentiment },
			function (response) {
				$sentence.addClass("classified")
			})
	})
}

/// Setup the progress indicator for the analyzer/importing entries
function setupAnalysisProgress() {
	if ($(".thread").length > 0) {
		var threadID = $(".thread").data("thread");
		var interval = setInterval(function() {
			updateAnalysisProgress(threadID, function() {
				clearInterval(interval)
			})
		}, 5000)
	}
}

/// Update the analysis progress
function updateAnalysisProgress(threadID, completion) {
	$.getJSON(
		'/progress-analyze/'+threadID,
		function (response) {
			var responsePercent = (response.percent_complete * 100).toFixed(2)
			$(".progress-container h1").text(`${responsePercent}% complete`)
			$(".progress-container h3").text(`Processing ${response.total_entries} Entries`)
			$("#analysis-progress").val(responsePercent)
			if (responsePercent == 100) {
				completion()
			}
		})
}