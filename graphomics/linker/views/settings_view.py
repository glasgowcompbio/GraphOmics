from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404

from linker.forms import ShareAnalysisForm
from linker.models import Analysis, Share

User = get_user_model()


def settings(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    share_analysis_form = ShareAnalysisForm()
    shares = Share.objects.filter(analysis=analysis)
    context = {
        'analysis_id': analysis.pk,
        'share_analysis_form': share_analysis_form,
        'shares': shares
    }
    return render(request, 'linker/settings.html', context)


def add_share(request, analysis_id):
    if request.method == 'POST':
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        form = ShareAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data['username']
            read_only = True if form.cleaned_data['share_type'] == 'True' else False

            # check username exists
            try:
                current_user = User.objects.get(username=username)
            except User.DoesNotExist:
                current_user = None
                messages.warning(request, 'Username %s does not exist' % username)

            if current_user is not None:
                try:
                    # try to get an existing share for this analysis under this user
                    share = Share.objects.get(analysis=analysis, user=current_user)
                    if not share.owner:
                        share.delete()  # if yes delete it, except for owner
                except Share.DoesNotExist:
                    share = None

                # now we can insert a new share
                share = Share(user=current_user, analysis=analysis, read_only=read_only, owner=False)
                share.save()

                if read_only:
                    messages.success(request, 'Analysis shared to %s in read-only mode' % current_user,
                                     extra_tags='primary')
                else:
                    messages.success(request, 'Analysis shared to %s in edit mode' % current_user,
                                     extra_tags='primary')

        else:
            messages.warning(request, 'Add share failed')

    return settings(request, analysis_id)


def delete_share(request, analysis_id, share_id):
    share = get_object_or_404(Share, pk=share_id)
    share.delete()
    messages.success(request, 'Share was successfully deleted', extra_tags='primary')
    return settings(request, analysis_id)
