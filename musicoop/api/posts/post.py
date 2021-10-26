"""
Módulo responsável por ações de login e obtenção do token do usuário
"""
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm.session import Session
from starlette import status

from musicoop.settings.logs import logging
from musicoop.database import get_db
from musicoop.schemas.post import PostSchema, PostCommentSchema
# from musicoop.schemas.user import GetUserSchema
from musicoop.controller.post import (get_posts, create_post,
                                         get_post_by_id)
from musicoop.controller.comment import get_comment_by_post
from musicoop.controller.contribuition import get_contribuitions_by_post, get_contribuition_by_id
# from musicoop.core.auth import get_current_user
from musicoop.utils.save_file import copy_file
from musicoop.utils.streamming import iterfile

logger = logging.getLogger(__name__)
router = APIRouter()
CHUNK_SIZE = 1024*1024
load_dotenv()

@router.get("/posts", status_code=status.HTTP_200_OK)
def get_post(database: Session = Depends(get_db)) -> PostCommentSchema:
    """
        Description
        -----------
        Parameters
        ----------
        Returns
        -------
        Raises
        ------
    """
    posts = get_posts(database)

    if not posts:
        raise HTTPException(
        status_code=status.HTTP_202_ACCEPTED,
        detail="retornou vazio"
    )

    list_posts = []
    for post in posts:
        comment = get_comment_by_post(post.id, database)
        contribuition = get_contribuitions_by_post(post.id, database)
        list_posts.append(PostCommentSchema.parse_obj({
        "id" : post.id,
        "post_name" : post.post_name,
        "file" : post.file,
        "file_size": post.file_size,
        "description": post.description,
        "user" : post.user,
        "creation_date" : str(post.creation_date),
        "comments": comment,
        "contribuitions" : contribuition
        }))

    return list_posts

@router.get("/post", status_code=status.HTTP_200_OK)
def getting_post_by_id(post_id:int,
                       database: Session = Depends(get_db)) -> PostCommentSchema:
    """
        Description
        -----------
        Parameters
        ----------
        Returns
        -------
        Raises
        ------
    """
    post = get_post_by_id(post_id, database)
    comment = get_comment_by_post(post_id, database)
    contribuition = get_contribuitions_by_post(post_id, database)

    if post is None:
        raise HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Erro ao buscar post"
    )

    return PostCommentSchema.parse_obj({
        "id" : post.id,
        "post_name" : post.post_name,
        "file" : post.file,
        "file_size": post.file_size,
        "description": post.description,
        "user" : post.user,
        "creation_date" : str(post.creation_date),
        "comments": comment,
        "contribuitions" : contribuition
    })

@router.post('/posts', status_code=status.HTTP_200_OK)
async def new_post(
                post_name: str = Form(...),
                description: str = Form(...),
                file: UploadFile = File(...),
                # current_user:GetUserSchema = Depends(get_current_user),
                database: Session = Depends(get_db)
                ) -> PostSchema:
    """
        Description
        -----------
        Parameters
        ----------
        Returns
        -------
        Raises
        ------
    """
    if file.content_type != "audio/mp3" and file.content_type != "audio/mpeg":
        raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Arquivo não é valido, apenas mp3!"
    )
    save_file, file_size = await copy_file(file, "post/")
    request = PostSchema.parse_obj({
        "post_name":post_name,
        "file":file.filename,
        "description": description,
        "file_size": file_size,
        "user":1
    })
    if save_file is False:
        raise HTTPException(
        status_code=status.HTTP_417_EXPECTATION_FAILED,
        detail="Erro ao salvar o arquivo no servidor, tente novamente!"
    )
    post = create_post(request, database)
    if post is None:
        raise HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Erro ao criar a música no banco de dados"
    )

    return request

@router.get('/musics', status_code=status.HTTP_206_PARTIAL_CONTENT)
def streamming_music(post_id: int = None,
                     contribuition_id: int = None,
                     database: Session = Depends(get_db),
                     range: str = Header(None)): # pylint: disable=redefined-builtin
    """
        Description
        -----------
        Parameters
        ----------
        Returns
        -------
        Raises
        ------
    """
    if post_id is None and contribuition_id is None:
        raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Precisa passar um post_id ou uma contribuition_id"
    )

    path_type = "post"
    post = get_post_by_id(post_id, database)
    if contribuition_id:
        path_type = "contribuition"
        post = get_contribuition_by_id(contribuition_id, database)
    if post is None:
        raise HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Erro ao reproduzir a música"
    )
    if range is None:
        start, end = CHUNK_SIZE, post.file_size
        if start > end:
            start, end = 0, CHUNK_SIZE
    else:
        start, end = range.replace("bytes=", "").split("-")
    start = int(start)
    end = int(end) if end else start + CHUNK_SIZE
    headers = {
            'Accept-Ranges': 'bytes',
            'Content-Range': f'bytes {str(start)}-{str(end)}/{str(post.file_size)}',
        }
    result_status = status.HTTP_206_PARTIAL_CONTENT
    if post.file_size < CHUNK_SIZE:
        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Range': f'bytes {str(0)}-{str(0)}/{str(post.file_size)}',
        }

    return StreamingResponse(iterfile(post.file, start, end, post.file_size, path_type),
                            headers=headers,
                            media_type="audio/mp3",
                            status_code=result_status)
