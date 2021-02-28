# Journal Analyzer

I've been keeping a daily journal for a few years now and decided to open source some of the analysis I've been doing on the records as well as keeping a easier to see format of the records.

## Setting up your own system

Depending on how you keep the format of your journal you'll need to do a few things.

### JSON

If your journal can be exported to JSON this is the easiest solution. Just create a file in `static/diary-download.json` and then implement your own class that implements the protocol `JournalRecord` in `importer.py`. You can see an example of this with `DailyDiaryJournalEntry`. 

### CSV

Effectively you'll need to build your own parser and just make each record conform to `JournalRecord` and just modify `import_entries` in `routes.py` to take the new format in. I'm looking to improve this so it's easier to modify but will work on that in the future

## Starting the app

1) Run Migrations. `flask db upgrade`
2) Start the app server `flask run`
3) In a web browser go to `/import` to start importing your records. 
4) Optional: In a web browser go to `/analyze` to analyze and fill in some additional information on your journal entries

You should be able to then see records on your localhost!

## Creating your own sentiment model

The default classifier model is the model provided by NLTK that was trained from various movie reviews. This isn't exactly precise on journal entries but it should work.

If you want to create your own sentiment model, then you can train your own data by going to: `/classify_sentences` and classifying your sentences as positive, negative or neutral. The neutral records are effectively ignored when analyzing your sentiment and it's important to get sufficient records. 

You can test the accuracy of your model by running `Classifier.test_local_classifier()` in a flask console (run `flask shell`).

If you're ready to use it, just modify `use_internal_classifier` in `main.js` to true. This is currently only used for local sentence analysis and not the graphs. 

## Things to do

- Simplifying how we send parameters down to the parameters. Send a dictionary down instead of having to provide individual arguments
- Expand models https://towardsdatascience.com/basic-binary-sentiment-analysis-using-nltk-c94ba17ae386
- Improve how `use_internal_classifier` is used instead of modifying js file. Expand use to other sentiment graphs.
- Prettier Graphs and colors.