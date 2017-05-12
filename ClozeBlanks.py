# -*- coding: utf-8 -*-
# See github page to report issues or to contribute:
# https://github.com/Arthaey/anki-cloze-blanks
#
# Also available for Anki at https://ankiweb.net/shared/info/546020849

# TODO: Seems not to work on normal cloze cards anymore...
import re
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction, QProgressDialog

from anki.hooks import addHook, wrap
from anki.utils import stripHTML
from aqt import mw
from aqt.editor import Editor
from aqt.utils import askUser, showInfo

FEATURES = {
    "unhideCloze" : True,
    "forNewCards" : False, # TODO: not yet implemented
    "forExistingCards" : True,
    "forSelectedCards" : True,
    "nonBreakingSpaces" : True,
}

BLANK = "_"
CARD_NAMES_SET = ["Cloze", "Epic Sentence"]
TEXT_FIELDS_SET = ["Text", "Sentence", "Front"]

ADD_BLANKS_MENU_TEXT = _(u"Add blanks to cloze notes")
UNHIDE_CLOZE_MENU_TEXT = _(u"Unhide clozed text in cloze notes")
CLOZE_WORDS_MENU_TEXT = _(u"Make each word into a cloze")

def _forExistingCards(prompt, funcForExistingCards):
    if not askUser(_(prompt)):
        return
    for name in CARD_NAMES_SET:
        model = mw.col.models.byName(name);
        nids = mw.col.models.nids(model)
        funcForExistingCards(nids)

def unhideClozeTextForSelectedCards(browser):
    nids = browser.selectedNotes()
    _unhideClozeTextInNotes(nids)

def processClozedText(text):
    # Only update clozes that do not already have hint text.
    # NOTE: Watch out for recursive cloze replacement
    regex = r"{{c(\d+)::(([^:{}]+?)(::[^:{}]*?)?)}}"
    return re.subn(regex, _unhideClozeTextMatch, text)

def _unhideClozeTextInField(note, text):
    newText, num = processClozedText(text)
    return newText

def updateClozeTextOnNoteField(note, currentField):
    original = note.fields[currentField]
    if note.hasTag("uncloze"):
        newText = _unhideClozeTextInField(note, original)
        if (note.fields[currentField] != newText):
            note.fields[currentField] = newText
            # logging.debug('Changed field from "'+unicode(original)+'" to "'+unicode(note.fields[currentField])+'"')
            return newText

def updateClozeTextFocusLost(modifiedOrNot, note, currentField):
    return updateClozeTextOnNoteField(note, currentField)

def updateClozeTextFocusGained(note, currentField):
    return updateClozeTextOnNoteField(note, currentField)

def updateClozeTextOnNote(note):
    text_fields = set(note.keys()).intersection(TEXT_FIELDS_SET)
    for field in text_fields:
        updateClozeTextOnNoteField(note, field)

def updateClozeTextTagsUpdated(note):
    return updateClozeTextOnNote(note)

def updateClozeTextNoteChanged(nid):
    note = mw.col.getNote(nid)
    updateClozeTextOnNote(note)

addHook("editFocusGained", updateClozeTextFocusGained)
addHook("editFocusLost", updateClozeTextFocusLost)
addHook("noteChanged", updateClozeTextNoteChanged)
# addHook("tagsUpdated", updateClozeTextTagsUpdated)

def unhideClozeTextForExistingCards():
    _forExistingCards(u"Unhide cloze text for ALL cloze cards?", _unhideClozeTextInNotes)

def _unhideClozeTextInNotes(nids):
    _updateExistingCards(UNHIDE_CLOZE_MENU_TEXT, nids, processClozedText)

def _unhideClozeTextMatch(match):
    num = match.group(1)
    text = match.group(3)
    return _unhideClozeText(num, text)

def _unhideClozeText(num, text):
    # Need to escape curly-braces.
    return u"{{{{c{0}::{1}::{2}}}}}".format(num, text, text)

def _updateExistingCards(checkpoint, nids, processFunc):
    updatedCount = 0
    mw.checkpoint(checkpoint)
    mw.progress.start()

    for nid in nids:
        note = mw.col.getNote(nid)
        text_fields = set(note.keys()).intersection(TEXT_FIELDS_SET)
        if len(text_fields) == 0:
            continue
        text_field = text_fields.pop()
        text = note[text_field]

        newText, num = processFunc(text)
        if text != newText:
            note[text_field] = newText
            note.flush()
            updatedCount += num

    mw.progress.finish()
    mw.reset()

    spacesNotice = ""
    if FEATURES["nonBreakingSpaces"]:
        spacesNotice = " and replaced spaces inside clozes with non-breaking spaces"
    showInfo(u"Updated {0} cards (from {1} cloze notes){2}.".format(
        updatedCount, len(nids), spacesNotice))


def _setupBrowserMenu(browser):
    unhideCloze = QAction(UNHIDE_CLOZE_MENU_TEXT, browser)
    browser.connect(unhideCloze, SIGNAL("triggered()"),
        lambda b = browser: unhideClozeTextForSelectedCards(b))

    browser.form.menuEdit.addSeparator()
    if FEATURES["unhideCloze"]:
        browser.form.menuEdit.addAction(unhideCloze)


if FEATURES["forNewCards"]:
    Editor.onCloze = wrap(Editor.onCloze, addClozeBlanksToNewCards, "before")
    # TODO: support making each word into a cloze

if FEATURES["forExistingCards"]:
    unhideCloze = QAction(UNHIDE_CLOZE_MENU_TEXT, mw)
    mw.connect(unhideCloze, SIGNAL("triggered()"), unhideClozeTextForExistingCards)

    mw.form.menuTools.addSeparator()
    if FEATURES["unhideCloze"]:
        mw.form.menuTools.addAction(unhideCloze)

if FEATURES["forSelectedCards"]:
    addHook("browser.setupMenus", _setupBrowserMenu)
