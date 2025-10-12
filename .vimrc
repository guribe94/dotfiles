" ---------------------- USABILITY CONFIGURATION ----------------------
"  Basic settings to provide a solid base for code editting
" don't make vim compatible with vi 
set nocompatible

"Enables syntax highlighting
:syntax on

"Enables line numbers on side
:set nu

"highlight the last used search pattern.
set hlsearch

" make vim try to detect file types and load plugins for them
filetype on
filetype plugin on
filetype indent on

"Enables omnicompletion
set omnifunc=syntaxcomplete#Complete

" When coding, auto-indent by 4 spaces, just like in K&R
" Note that this does NOT change tab into 4 spaces
" You can do that with "set tabstop=4"
set shiftwidth=4

" Always replace tab with 8 spaces, except for makefiles
"set expandtab
" reload files changed outside vim
set autoread         

" encoding is utf 8
set encoding=utf-8
set fileencoding=utf-8


" set unix line endings
set fileformat=unix

" when reading files try unix line endings then dos, also use unix for new
" buffers
set fileformats=unix,dos


autocmd FileType make setlocal noexpandtab

" Ignore case when searching
" - override this setting by tacking on \c or \C to your search term to make
"   your search always case-insensitive or case-sensitive, respectively.
set ignorecase

"Set the max line length at 80 characters
set textwidth=80


" In many terminal emulators the mouse works just fine, thus enable it.
if has('mouse')
  set mouse=a
endif

"Improves vim lag - any action that is not typed will not cause the screen to redraw.
set lazyredraw

"Tells vim that the terminal is able to handle having more characters sent to the screen for redrawing.
set ttyfast

" Convenient command to see the difference between the current buffer and the
" file it was loaded from, thus the changes you made.
" Only define it when not defined already.
if !exists(":DiffOrig")
  command DiffOrig vert new | set bt=nofile | r # | 0d_ | diffthis
                  \ | wincmd p | diffthis
endif
" Don't do spell-checking on Vim help files
autocmd FileType help setlocal nospell

" Prepend ~/.backup to backupdir so that Vim will look for that directory
" before littering the current dir with backups.
set backupdir^=~/.backup
" Also use ~/.backup for swap files. The trailing // tells Vim to incorporate
" full path into swap file names.
set dir^=~/.backup//
" Ignore case when searching
" - override this setting by tacking on \c or \C to your search term to make
"   your search always case-insensitive or case-sensitive, respectively.
set ignorecase
"Disable vi backspace setings so all characters can be backspaced not just the
"ones that were entered during that insert session
set backspace=2
