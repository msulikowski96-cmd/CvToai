import logging
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF file
    
    Args:
        file_path (str): Path to the PDF file
    
    Returns:
        str: Extracted text from PDF or None if extraction fails
    """
    try:
        text = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                logger.warning("PDF jest zaszyfrowany - próba otworzenia bez hasła")
                try:
                    pdf_reader.decrypt('')
                except:
                    logger.error("Nie udało się otworzyć zaszyfrowanego PDF")
                    return None
            
            # Extract text from all pages
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text:
                        text += page_text + "\n"
                        logger.debug(f"Wyodrębniono tekst ze strony {page_num + 1}")
                
                except Exception as e:
                    logger.warning(f"Błąd odczytywania strony {page_num + 1}: {str(e)}")
                    continue
        
        # Clean up the text
        text = text.strip()
        
        if not text:
            logger.error("Nie udało się wyodrębnić tekstu z PDF")
            return None
        
        # Basic text cleanup
        text = clean_extracted_text(text)
        
        logger.info(f"Pomyślnie wyodrębniono tekst z PDF (długość: {len(text)} znaków)")
        return text
    
    except Exception as e:
        logger.error(f"Błąd podczas ekstrakcji tekstu z PDF: {str(e)}")
        return None

def extract_text_from_pdf_bytes(pdf_bytes):
    """
    Extract text from PDF bytes
    
    Args:
        pdf_bytes (bytes): PDF file as bytes
    
    Returns:
        str: Extracted text from PDF or None if extraction fails
    """
    try:
        text = ""
        
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Check if PDF is encrypted
        if pdf_reader.is_encrypted:
            logger.warning("PDF jest zaszyfrowany - próba otworzenia bez hasła")
            try:
                pdf_reader.decrypt('')
            except:
                logger.error("Nie udało się otworzyć zaszyfrowanego PDF")
                return None
        
        # Extract text from all pages
        for page_num in range(len(pdf_reader.pages)):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                
                if page_text:
                    text += page_text + "\n"
                    logger.debug(f"Wyodrębniono tekst ze strony {page_num + 1}")
            
            except Exception as e:
                logger.warning(f"Błąd odczytywania strony {page_num + 1}: {str(e)}")
                continue
        
        # Clean up the text
        text = text.strip()
        
        if not text:
            logger.error("Nie udało się wyodrębnić tekstu z PDF")
            return None
        
        # Basic text cleanup
        text = clean_extracted_text(text)
        
        logger.info(f"Pomyślnie wyodrębniono tekst z PDF (długość: {len(text)} znaków)")
        return text
    
    except Exception as e:
        logger.error(f"Błąd podczas ekstrakcji tekstu z PDF: {str(e)}")
        return None

def clean_extracted_text(text):
    """
    Clean up extracted text from PDF
    
    Args:
        text (str): Raw extracted text
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:  # Skip empty lines
            lines.append(line)
    
    # Join lines with single line breaks
    cleaned_text = '\n'.join(lines)
    
    # Remove excessive spaces
    import re
    cleaned_text = re.sub(r' +', ' ', cleaned_text)
    
    return cleaned_text

def validate_pdf_file(file_path):
    """
    Validate if file is a proper PDF
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        bool: True if valid PDF, False otherwise
    """
    try:
        with open(file_path, 'rb') as file:
            # Check if file starts with PDF header
            header = file.read(4)
            if header != b'%PDF':
                logger.error("Plik nie ma poprawnego nagłówka PDF")
                return False
            
            # Try to read with PyPDF2
            file.seek(0)
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check if we can get number of pages
            page_count = len(pdf_reader.pages)
            logger.debug(f"Plik PDF zawiera {page_count} stron")
            
            return page_count > 0
    
    except Exception as e:
        logger.error(f"Błąd walidacji pliku PDF: {str(e)}")
        return False
