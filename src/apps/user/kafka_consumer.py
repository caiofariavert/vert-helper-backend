import json

from django_kafka.consumer import Consumer, Message


def user_consumer(consumer: Consumer, msg: Message) -> None:

    user_data = json.loads(msg.value())

    try:
        create_or_update_user(user_data)
        consumer.commit(message=msg)
        print(f"User {user_data['email']} created/updated")
    except Exception as e:
        print(e)


def save_image_from_url_to_model(user, url) -> None:
    import uuid
    from tempfile import NamedTemporaryFile
    from urllib.request import urlopen

    from django.core.files import File

    if url in ["", None]:
        return

    img_extension = url.split(".")[-1]

    img_temp = NamedTemporaryFile(delete=True)
    img_temp.write(urlopen(url).read())
    img_temp.flush()
    user.image.save(
        f"{uuid.uuid4()}.{img_extension}",
        content=File(img_temp),
        save=True,
    )


def create_or_update_user(user_data: dict) -> None:
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if User.objects.filter(email=user_data["email"]).exists():
        user = User.objects.get(email=user_data["email"])
    else:
        user = User()

    user.email = user_data["email"]
    user.name = user_data["name"]
    user.is_active = user_data["is_active"]
    user.save()

    if "image" in user_data:
        try:
            save_image_from_url_to_model(user, user_data["image"])
        except Exception as e:
            print("error on save image: ", e)
