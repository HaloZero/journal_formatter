/* classify.html only */

$(function() {
	setupClassify()
});

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
