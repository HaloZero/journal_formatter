$(function() {
	setupNav()
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
