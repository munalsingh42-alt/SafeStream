from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Movie


def home(request):

    movies = Movie.objects.all()

    genres = request.GET.getlist('genre')

    languages = request.GET.getlist('language')

    sort = request.GET.get('sort')

    if genres:

        movies = movies.filter(
            genre__in=genres
        )

    if languages:

        movies = movies.filter(
            language__in=languages
        )

    if sort == 'title':

        movies = movies.order_by('title')

    elif sort == '-title':

        movies = movies.order_by('-title')

    else:

        movies = movies.order_by('-id')

    paginator = Paginator(
        movies,
        6
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    all_genres = Movie.objects.values_list(
        'genre',
        flat=True
    ).distinct()

    all_languages = Movie.objects.values_list(
        'language',
        flat=True
    ).distinct()

    genre_counts = []

    for genre in all_genres:

        genre_counts.append({

            'name': genre,

            'count': Movie.objects.filter(
                genre=genre
            ).count()

        })

    language_counts = []

    for language in all_languages:

        language_counts.append({

            'name': language,

            'count': Movie.objects.filter(
                language=language
            ).count()

        })

    return render(

        request,

        'movies/home.html',

        {

            'page_obj': page_obj,

            'genres': all_genres,

            'languages': all_languages,

            'selected_genres': genres,

            'selected_languages': languages,

            'genre_counts': genre_counts,

            'language_counts': language_counts

        }

    )