/* status.html only */

$(function() {
	setupStatusPage()
});

/// Setup the /status page: date-range filtering, row selection, and
/// wiring "Analyze Selected" to only the checked entries.
function setupStatusPage() {
	if ($('.table-container').length === 0 || $('.entry-select').length === 0) {
		return
	}

	$('#filter-start-date, #filter-end-date').on('change', applyDateFilter)
	$('#clear-date-filter').on('click', function() {
		$('#filter-start-date, #filter-end-date').val('')
		applyDateFilter()
	})

	$('#select-all').on('change', function() {
		var checked = $(this).prop('checked')
		visibleRows().find('.entry-select').prop('checked', checked)
		updateSelectionState()
	})

	$('#select-unanalyzed').on('click', function() {
		$('.entry-select').prop('checked', false)
		visibleRows().filter('[data-analyzed="false"]').find('.entry-select').prop('checked', true)
		updateSelectionState()
	})

	$('.entry-select').on('change', updateSelectionState)

	$('#analyze-selected-form').on('submit', function() {
		var ids = selectedEntryIds()
		$('#entry-ids-field').val(ids.join(','))
	})

	updateSelectionState()
}

function visibleRows() {
	return $('.table-container tbody tr').filter(function() {
		return $(this).css('display') !== 'none'
	})
}

function applyDateFilter() {
	var startDate = $('#filter-start-date').val()
	var endDate = $('#filter-end-date').val()

	$('.table-container tbody tr').each(function() {
		var rowDate = $(this).data('date')
		var visible = (!startDate || rowDate >= startDate) && (!endDate || rowDate <= endDate)
		$(this).toggle(visible)
	})

	updateSelectionState()
}

function selectedEntryIds() {
	return $('.entry-select:checked').map(function() {
		return $(this).val()
	}).get()
}

function updateSelectionState() {
	var count = selectedEntryIds().length
	$('#selected-count').text(count + (count == 1 ? ' entry selected' : ' entries selected'))
	$('#analyze-selected-button').prop('disabled', count === 0)
}
