/* analyze.html only */

$(function() {
	setupAnalysisProgress()
});

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
