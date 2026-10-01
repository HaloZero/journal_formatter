$(function() {
	setupNav()
	setupAnalyze()
});

/// setup the hamburger toggle and the Charts dropdown/accordion in the nav
function setupNav() {
	$('.nav-toggle').on('click', function() {
		var $nav = $('.main-nav')
		var isOpen = $nav.toggleClass('open').hasClass('open')
		$(this).attr('aria-expanded', isOpen)
	})

	$('.nav-group-toggle').on('click', function(event) {
		event.stopPropagation()
		var $group = $(this).closest('.nav-group')
		var isOpen = $group.toggleClass('open').hasClass('open')
		$(this).attr('aria-expanded', isOpen)
	})

	// clicking anywhere outside the Charts group closes it
	$(document).on('click', function(event) {
		var $group = $('.nav-group')
		if (!$(event.target).closest($group).length) {
			$group.removeClass('open')
			$group.find('.nav-group-toggle').attr('aria-expanded', false)
		}
	})
}

/// setup the button to analyze a journal entry (used on the entry list
/// and day-in-history pages, via _entry.html)
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
