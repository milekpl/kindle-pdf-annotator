# Announcing Kindle PDF Annotator

As an academic, I've always had a love-hate relationship with PDFs. On one hand, they're the standard format for research papers, theses, and dissertations. On the other hand, they're inflexible and difficult to work with when it comes to annotation. But as researchers, we must make notes and highlights when reading these documents – it's an essential part of our work. Printing them out and marking them up is impractical, and using a computer or tablet for annotation is just not as enjoyable as reading on an e-ink Kindle. At least I cannot read papers on computers or tablets. They are too distracting and make it hard to focus.

## The Kindle Solution (With a Major Drawback)

I found that the Kindle was an excellent tool for annotating academic papers. You can highlight text, add notes, and bookmark important sections while reading. The e-ink display is easy on the eyes during long reading sessions, and the annotation tools are quite good.

There's a significant problem, however. While the Kindle is great for reading and annotating PDFs, it stores these annotations in stand-off fashion in sidecar files on your device rather than embedding them directly into the PDF. This means you can't share the annotated PDF with colleagues, students, or integrate them back into reference managers like Zotero, which would otherwise be able to extract these annotations and incorporate them into its database.

The multi-column layouts in research papers do look terrible on Kindles (though EPUBs work nicely, they're unfortunately not as common in academic publishing). But even with this visual limitation, I found the Kindle annotation experience superior to PDF annotation tools on computers or tablets. The problem was getting those annotations back into the original PDF format.

## Introducing Kindle PDF Annotator

After years of frustration with this workflow gap, I decided to solve the problem myself. I created the Kindle PDF Annotator – an application that extracts your Kindle annotations from PDS files (Kindle Reader Data Store) and MyClippings.txt, and embeds them back into the original PDF with pixel-perfect positioning.

This application is unique because there's no other tool that does this specific job as comprehensively. It features:

- **Complete Annotation Support**: Extracts and preserves notes, highlights, and bookmarks from Kindle
- **Precise Amazon Coordinate System**: Converts Kindle coordinates to PDF coordinates with 0.1-0.5 point precision
- **Multiple Input Sources**: Processes both PDS files and MyClippings.txt
- **Accurate Positioning**: Uses actual Kindle annotation dimensions instead of fixed rectangles
- **PDF Navigation Bookmarks**: Creates real PDF bookmarks visible in all PDF viewers
- **Both GUI and CLI**: Available with both graphical interface and command-line tool

## Reverse Engineering the Kindle Coordinate System

The application uses Amazon's coordinate system with an inches×100 encoding system, achieving sub-millimeter positioning accuracy (0.1-0.5 points). This precision ensures that highlights appear exactly where they should on the PDF, maintaining the connection between your annotations and the original text.

The tool has been thoroughly tested with 140 unit tests ensuring reliable and accurate annotation placement. But since the sidecar files are not officially documented, it's imperfect. I had to reverse engineer this myself. Apparently, the preferred coordinate system for Kindles uses inches.

## Compatibility

The application currently works with Kindle Paperwhite (6th generation). Your mileage may vary if you have a newer device, as Amazon has changed formats between generations. Older devices used different file formats, and for those, there's a Java application available for extracting annotations: [kindle-annotations](https://code.google.com/archive/p/kindle-annotations/).

## Get Started

If you're an academic, researcher, or anyone who uses a Kindle to annotate PDFs, this tool will revolutionize your workflow. No more manually recreating highlights in your reference manager or sending un-annotated PDFs to colleagues.

You can find the complete documentation, installation instructions, and usage examples in [the repository](https://github.com/milekpl/kindle-pdf-annotator/). The tool is open-source under the GPL v3 license. I won't beg you to star the project, but you can. The software package requires you to have Python installed.

Academic work requires deep engagement with texts, and that means annotating, highlighting, and note-taking. With Kindle PDF Annotator, the best of both worlds – the excellent reading experience of Kindle and the shareable, integrated workflow of annotated PDFs – are now possible.

No more frustration with disconnected annotation workflows. Your Kindle annotations can finally live where they belong – in the PDF itself.