from orcaverify.checks._text import claims


def test_splits_plain_sentences():
    assert claims("The sky is blue. It is sunny.") == ["The sky is blue.", "It is sunny."]


def test_does_not_split_after_title_abbreviation():
    # "Dr." must not become its own bare claim.
    assert claims("Dr. Smith joined the firm in 2010.") == ["Dr. Smith joined the firm in 2010."]


def test_does_not_split_after_acronym():
    assert claims("The company operates in the U.S. and Canada.") == [
        "The company operates in the U.S. and Canada."
    ]


def test_still_splits_when_word_merely_ends_in_a_common_word():
    # "no" is a real word, not treated as the "No." abbreviation.
    assert claims("The answer is no. It failed.") == ["The answer is no.", "It failed."]
